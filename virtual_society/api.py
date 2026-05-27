from __future__ import annotations

import json
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .agent_dossiers import build_agent_dossier, build_agent_dossiers
from .health import assess_metrics
from .history import HistoryRecorder
from .interventions import Intervention
from .observer3d import render_observer3d_html
from .observer import render_observer_html
from .reports import build_run_record, render_run_html
from .simulation import Simulation
from .world_dossiers import (
    build_location_dossier,
    build_location_dossiers,
    build_organization_dossier,
    build_organization_dossiers,
)


class SimulationService:
    """Stateful local API boundary around one deterministic simulation."""

    def __init__(
        self,
        seed: int = 1,
        snapshot_interval_days: int = 30,
        world_preset: str = "base",
    ) -> None:
        if snapshot_interval_days < 1:
            raise ValueError("snapshot_interval_days must be >= 1")
        self.seed = seed
        self.world_preset = world_preset
        self.snapshot_interval_days = snapshot_interval_days
        self._lock = threading.RLock()
        self._reset_locked(seed)

    def reset(
        self,
        seed: int | None = None,
        world_preset: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if world_preset is not None:
                self.world_preset = world_preset
            self._reset_locked(self.seed if seed is None else seed)
            return self.state()

    def state(self) -> dict[str, Any]:
        with self._lock:
            payload = self.simulation.snapshot()
            payload["world_preset"] = self.world_preset
            payload["pending_interventions"] = [
                _intervention_dict(intervention)
                for intervention in self.pending_interventions
            ]
            payload["metrics_history_length"] = len(self.metrics_history)
            return payload

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "seed": self.seed,
                "metrics": [asdict(metric) for metric in self.metrics_history],
                "final_metrics": (
                    asdict(self.metrics_history[-1])
                    if self.metrics_history
                    else asdict(self.simulation.metrics())
                ),
            }

    def events(self, limit: int = 50) -> dict[str, Any]:
        with self._lock:
            events = self.simulation.world.event_log[-max(0, limit):]
            return {
                "seed": self.seed,
                "day": self.simulation.world.day,
                "events": [asdict(event) for event in events],
            }

    def history(self) -> dict[str, Any]:
        with self._lock:
            return self.history_recorder.record(self.metrics_history)

    def run_record(self) -> dict[str, Any]:
        with self._lock:
            findings = assess_metrics(self.metrics_history)
            return build_run_record(
                self.seed,
                self.metrics_history,
                self.simulation.world,
                findings,
                history=self.history_recorder.record(self.metrics_history),
            )

    def agent_dossier(self, agent_id: str) -> dict[str, Any]:
        with self._lock:
            record = self.run_record()
            return build_agent_dossier(
                self.simulation.world,
                agent_id,
                seed=self.seed,
                relationship_links=record.get("relationship_links", []),
                observer_recommendations=record.get("observer_recommendations", []),
            )

    def agent_dossiers(self) -> dict[str, Any]:
        with self._lock:
            record = self.run_record()
            return build_agent_dossiers(
                self.simulation.world,
                seed=self.seed,
                observer_recommendations=record.get("observer_recommendations", []),
            )

    def location_dossier(self, location_id: str) -> dict[str, Any]:
        with self._lock:
            return build_location_dossier(
                self.simulation.world,
                location_id,
                seed=self.seed,
            )

    def location_dossiers(self) -> dict[str, Any]:
        with self._lock:
            return build_location_dossiers(self.simulation.world, seed=self.seed)

    def organization_dossier(self, organization_id: str) -> dict[str, Any]:
        with self._lock:
            return build_organization_dossier(
                self.simulation.world,
                organization_id,
                seed=self.seed,
            )

    def organization_dossiers(self) -> dict[str, Any]:
        with self._lock:
            return build_organization_dossiers(self.simulation.world, seed=self.seed)

    def step(
        self,
        days: int = 1,
        interventions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if days < 1:
            raise ValueError("days must be >= 1")

        with self._lock:
            current_day = self.simulation.world.day
            end_day = current_day + days
            new_interventions = [
                self._intervention_from_payload(item, default_day=current_day + 1)
                for item in interventions or []
            ]
            run_interventions: list[Intervention] = []
            remaining: list[Intervention] = []
            for intervention in [*self.pending_interventions, *new_interventions]:
                if current_day < intervention.day <= end_day:
                    run_interventions.append(intervention)
                else:
                    remaining.append(intervention)
            self.pending_interventions = remaining

            new_metrics = self.simulation.run(
                days,
                interventions=run_interventions,
                after_step=self.history_recorder.capture,
            )
            self.metrics_history.extend(new_metrics)
            return {
                "seed": self.seed,
                "days_advanced": days,
                "current_day": self.simulation.world.day,
                "metrics": [asdict(metric) for metric in new_metrics],
                "final_metrics": asdict(new_metrics[-1]),
                "applied_interventions": [
                    _intervention_dict(intervention)
                    for intervention in run_interventions
                ],
                "pending_interventions": [
                    _intervention_dict(intervention)
                    for intervention in self.pending_interventions
                ],
            }

    def schedule_intervention(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            intervention = self._intervention_from_payload(
                payload,
                default_day=self.simulation.world.day + 1,
            )
            if intervention.day <= self.simulation.world.day:
                raise ValueError("scheduled intervention day must be in the future")
            self.pending_interventions.append(intervention)
            self.pending_interventions.sort(key=lambda item: item.day)
            return {
                "scheduled": _intervention_dict(intervention),
                "pending_interventions": [
                    _intervention_dict(item)
                    for item in self.pending_interventions
                ],
            }

    def _reset_locked(self, seed: int) -> None:
        self.seed = seed
        self.simulation = Simulation(seed=seed, world_preset=self.world_preset)
        self.metrics_history: list = []
        self.pending_interventions: list[Intervention] = []
        self.history_recorder = HistoryRecorder(
            seed=seed,
            interval_days=self.snapshot_interval_days,
        )

    def _intervention_from_payload(
        self,
        payload: dict[str, Any],
        default_day: int,
    ) -> Intervention:
        data = dict(payload)
        data.setdefault("day", default_day)
        return Intervention.from_dict(data)


def make_server(
    service: SimulationService,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _handler_class(service))


def run_server(
    seed: int = 1,
    host: str = "127.0.0.1",
    port: int = 8765,
    snapshot_interval_days: int = 30,
    world_preset: str = "base",
) -> None:
    service = SimulationService(
        seed=seed,
        snapshot_interval_days=snapshot_interval_days,
        world_preset=world_preset,
    )
    server = make_server(service, host=host, port=port)
    print(f"Virtual society API listening on http://{host}:{server.server_port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _handler_class(service: SimulationService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "VirtualSocietyAPI/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path in {"", "/"}:
                    self._send_json(_index())
                    return
                if parsed.path == "/health":
                    self._send_json({"status": "ok", "day": service.simulation.world.day})
                    return
                if parsed.path == "/state":
                    self._send_json(service.state())
                    return
                if parsed.path == "/metrics":
                    self._send_json(service.metrics())
                    return
                if parsed.path == "/events":
                    limit = int(query.get("limit", ["50"])[0])
                    self._send_json(service.events(limit=limit))
                    return
                if parsed.path == "/history":
                    self._send_json(service.history())
                    return
                if parsed.path == "/report/run.json":
                    self._send_json(service.run_record())
                    return
                if parsed.path == "/report/run.html":
                    self._send_text(
                        render_run_html(service.run_record()),
                        content_type="text/html; charset=utf-8",
                    )
                    return
                if parsed.path == "/agents":
                    self._send_json(service.agent_dossiers())
                    return
                if parsed.path.startswith("/agents/"):
                    agent_id = unquote(parsed.path.removeprefix("/agents/"))
                    if not agent_id:
                        raise ValueError("agent id is required")
                    self._send_json(service.agent_dossier(agent_id))
                    return
                if parsed.path == "/locations":
                    self._send_json(service.location_dossiers())
                    return
                if parsed.path.startswith("/locations/"):
                    location_id = unquote(parsed.path.removeprefix("/locations/"))
                    if not location_id:
                        raise ValueError("location id is required")
                    self._send_json(service.location_dossier(location_id))
                    return
                if parsed.path == "/organizations":
                    self._send_json(service.organization_dossiers())
                    return
                if parsed.path.startswith("/organizations/"):
                    organization_id = unquote(parsed.path.removeprefix("/organizations/"))
                    if not organization_id:
                        raise ValueError("organization id is required")
                    self._send_json(service.organization_dossier(organization_id))
                    return
                if parsed.path == "/observer":
                    self._send_text(
                        render_observer_html(),
                        content_type="text/html; charset=utf-8",
                    )
                    return
                if parsed.path == "/observer3d":
                    self._send_text(
                        render_observer3d_html(),
                        content_type="text/html; charset=utf-8",
                    )
                    return
                self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            except Exception as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_OPTIONS(self) -> None:
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_common_headers()
            self.end_headers()

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                payload = self._read_json()
                if parsed.path == "/step":
                    days = int(payload.get("days", 1))
                    interventions = payload.get("interventions", [])
                    if not isinstance(interventions, list):
                        raise ValueError("interventions must be a list")
                    self._send_json(service.step(days=days, interventions=interventions))
                    return
                if parsed.path == "/interventions":
                    if "interventions" in payload:
                        items = payload["interventions"]
                        if not isinstance(items, list):
                            raise ValueError("interventions must be a list")
                        result = [
                            service.schedule_intervention(item)
                            for item in items
                        ]
                        self._send_json({"scheduled": result})
                    else:
                        self._send_json(service.schedule_intervention(payload))
                    return
                if parsed.path == "/reset":
                    seed = payload.get("seed")
                    preset = payload.get("world_preset")
                    self._send_json(
                        service.reset(
                            seed=int(seed) if seed is not None else None,
                            world_preset=str(preset) if preset is not None else None,
                        )
                    )
                    return
                self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            except Exception as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("content-length", "0"))
            if length == 0:
                return {}
            data = self.rfile.read(length)
            payload = json.loads(data.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self._send_common_headers()
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(
            self,
            body: str,
            status: HTTPStatus = HTTPStatus.OK,
            content_type: str = "text/plain; charset=utf-8",
        ) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self._send_common_headers()
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            self._send_json(
                {"error": message, "status": int(status)},
                status=status,
            )

        def _send_common_headers(self) -> None:
            self.send_header("access-control-allow-origin", "*")
            self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
            self.send_header("access-control-allow-headers", "content-type")

    return Handler


def _index() -> dict[str, Any]:
    return {
        "name": "Virtual Society API",
        "endpoints": {
            "GET /health": "service status",
            "GET /state": "current simulation snapshot",
            "GET /metrics": "metrics recorded through API stepping",
            "GET /events?limit=50": "recent events",
            "GET /history": "periodic history snapshots",
            "GET /report/run.json": "run report JSON",
            "GET /report/run.html": "run report HTML",
            "GET /agents": "read-only agent dossier index",
            "GET /agents/{id}": "read-only agent dossier with life journal and relationships",
            "GET /locations": "read-only location dossier index",
            "GET /locations/{id}": "read-only location dossier with route and affordance data",
            "GET /organizations": "read-only organization dossier index",
            "GET /organizations/{id}": "read-only organization dossier with member and affordance data",
            "GET /observer": "interactive browser observer",
            "GET /observer3d": "Three.js 3D observer prototype",
            "POST /step": {"days": 1, "interventions": []},
            "POST /interventions": "schedule a future intervention",
            "POST /reset": {"seed": 1},
            "POST /reset generative alpha": {"seed": 1, "world_preset": "generative_alpha"},
        },
    }


def _intervention_dict(intervention: Intervention) -> dict[str, Any]:
    return {
        "day": intervention.day,
        "kind": intervention.kind,
        "params": dict(intervention.params),
        "reason": intervention.reason,
        "actor_id": intervention.actor_id,
    }
