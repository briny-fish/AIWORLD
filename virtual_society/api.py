from __future__ import annotations

import json
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .agent_dossiers import build_agent_dossier, build_agent_dossiers
from .generative_chain_evaluation import assess_generated_chains
from .health import assess_metrics
from .history import HistoryRecorder
from .interventions import Intervention
from .observer3d import render_observer3d_html
from .observer import render_observer_html
from .reports import build_run_record, render_run_html
from .simulation import Simulation
from .social_timeline import build_agent_social_history, build_social_feed
from .world_client_protocol import build_world_client_frame
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
        cognition: Any = None,
        reflection: Any = None,
        dialogue: Any = None,
    ) -> None:
        if snapshot_interval_days < 1:
            raise ValueError("snapshot_interval_days must be >= 1")
        self.seed = seed
        self.world_preset = world_preset
        self.snapshot_interval_days = snapshot_interval_days
        self.cognition = cognition
        self.reflection = reflection
        self.dialogue = dialogue
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
            cognition_trace = _provider_trace(self.cognition)
            reflection_trace = _provider_trace(self.reflection)
            dialogue_trace = _provider_trace(self.dialogue)
            generated_chains = [
                item.as_dict()
                for item in assess_generated_chains(
                    self.simulation.world,
                    dialogue_trace,
                    reflection_trace,
                )
            ]
            return build_run_record(
                self.seed,
                self.metrics_history,
                self.simulation.world,
                findings,
                history=self.history_recorder.record(self.metrics_history),
                cognition_trace=cognition_trace,
                counterfactual_evaluation=None,
                reflection_trace=reflection_trace,
                dialogue_trace=dialogue_trace,
                generated_chains=generated_chains,
                llm_cache=_llm_cache_summary(
                    self.cognition,
                    self.reflection,
                    self.dialogue,
                ),
            )

    def provider_status(self) -> dict[str, Any]:
        with self._lock:
            surfaces = {
                "cognition": _provider_status("cognition", self.cognition),
                "reflection": _provider_status("reflection", self.reflection),
                "dialogue": _provider_status("dialogue", self.dialogue),
            }
            models = sorted(
                {
                    str(item.get("model"))
                    for item in surfaces.values()
                    if item.get("model")
                }
            )
            return {
                "kind": "provider_status",
                "seed": self.seed,
                "day": self.simulation.world.day,
                "world_preset": self.world_preset,
                "live_llm_enabled": any(
                    item.get("mode") == "hybrid"
                    for item in surfaces.values()
                ),
                "models": models,
                "surfaces": surfaces,
            }

    def world_client_frame(self) -> dict[str, Any]:
        with self._lock:
            record = self.run_record()
            return build_world_client_frame(
                self.simulation.world,
                seed=self.seed,
                world_preset=self.world_preset,
                provider_status=self.provider_status(),
                social_feed=record.get("social_feed"),
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
                dialogue_trace=record.get("dialogue_trace", []),
                generated_chains=record.get("generated_chains", []),
            )

    def agent_dossiers(self) -> dict[str, Any]:
        with self._lock:
            record = self.run_record()
            return build_agent_dossiers(
                self.simulation.world,
                seed=self.seed,
                observer_recommendations=record.get("observer_recommendations", []),
                dialogue_trace=record.get("dialogue_trace", []),
                generated_chains=record.get("generated_chains", []),
            )

    def social_feed(self, limit: int = 50) -> dict[str, Any]:
        with self._lock:
            record = self.run_record()
            payload = build_social_feed(
                self.simulation.world,
                dialogue_trace=record.get("dialogue_trace", []),
                generated_chains=record.get("generated_chains", []),
                limit=limit,
            )
            payload["seed"] = self.seed
            return payload

    def agent_social_history(self, agent_id: str, limit: int = 20) -> dict[str, Any]:
        with self._lock:
            record = self.run_record()
            payload = build_agent_social_history(
                self.simulation.world,
                agent_id,
                dialogue_trace=record.get("dialogue_trace", []),
                generated_chains=record.get("generated_chains", []),
                limit=limit,
            )
            payload["seed"] = self.seed
            return payload

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
        self.simulation = Simulation(
            seed=seed,
            world_preset=self.world_preset,
            cognition=self.cognition,
            reflection=self.reflection,
            dialogue=self.dialogue,
        )
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
    cognition: Any = None,
    reflection: Any = None,
    dialogue: Any = None,
) -> None:
    service = SimulationService(
        seed=seed,
        snapshot_interval_days=snapshot_interval_days,
        world_preset=world_preset,
        cognition=cognition,
        reflection=reflection,
        dialogue=dialogue,
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
                if parsed.path == "/provider-status":
                    self._send_json(service.provider_status())
                    return
                if parsed.path == "/social-feed":
                    limit = int(query.get("limit", ["50"])[0])
                    self._send_json(service.social_feed(limit=limit))
                    return
                if parsed.path == "/client/world-frame":
                    self._send_json(service.world_client_frame())
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
                if parsed.path.startswith("/agents/") and parsed.path.endswith("/social-history"):
                    agent_id = unquote(
                        parsed.path.removeprefix("/agents/").removesuffix("/social-history")
                    ).rstrip("/")
                    if not agent_id:
                        raise ValueError("agent id is required")
                    limit = int(query.get("limit", ["20"])[0])
                    self._send_json(service.agent_social_history(agent_id, limit=limit))
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


def _provider_status(surface: str, provider: Any) -> dict[str, Any]:
    if provider is None:
        return {
            "surface": surface,
            "mode": "rule",
            "provider": "rule",
            "model": "",
            "stats": {},
            "trace_length": 0,
        }
    primary = getattr(provider, "primary", provider)
    stats = _dataclass_dict(getattr(provider, "stats", None))
    config = _dataclass_dict(getattr(provider, "config", None))
    return {
        "surface": surface,
        "mode": "hybrid" if primary is not provider else "direct",
        "provider": provider.__class__.__name__,
        "primary_provider": primary.__class__.__name__,
        "model": str(getattr(primary, "model", "")),
        "reasoning_effort": str(getattr(primary, "reasoning_effort", "")),
        "stats": stats,
        "config": config,
        "trace_length": len(getattr(provider, "trace", []) or []),
        "cache": _cache_status(primary),
    }


def _provider_trace(provider: Any) -> list[dict[str, Any]]:
    trace = getattr(provider, "trace", None)
    if not trace:
        return []
    return [
        item.as_dict() if hasattr(item, "as_dict") else dict(item)
        for item in trace
    ]


def _llm_cache_summary(*providers: Any) -> list[dict[str, Any]]:
    items = []
    for surface, provider in zip(("cognition", "reflection", "dialogue"), providers):
        if provider is None:
            continue
        primary = getattr(provider, "primary", provider)
        cache = getattr(primary, "cache", None)
        if cache is None:
            continue
        stats = cache.stats
        items.append(
            {
                "surface": surface,
                "provider": cache.provider,
                "mode": cache.mode,
                "root_dir": str(cache.root_dir),
                "model": getattr(primary, "model", ""),
                "reasoning_effort": getattr(primary, "reasoning_effort", "") or "default",
                "reads": stats.reads,
                "hits": stats.hits,
                "misses": stats.misses,
                "writes": stats.writes,
            }
        )
    return items


def _cache_status(primary: Any) -> dict[str, Any]:
    cache = getattr(primary, "cache", None)
    if cache is None:
        return {}
    return {
        "provider": cache.provider,
        "mode": cache.mode,
        "root_dir": str(cache.root_dir),
        "stats": _dataclass_dict(cache.stats),
    }


def _dataclass_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return _jsonable(value)
    return {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(_jsonable(item) for item in value)
    return value


def _index() -> dict[str, Any]:
    return {
        "name": "Virtual Society API",
        "endpoints": {
            "GET /health": "service status",
            "GET /state": "current simulation snapshot",
            "GET /metrics": "metrics recorded through API stepping",
            "GET /events?limit=50": "recent events",
            "GET /social-feed?limit=50": "readable social feed with dialogue and influence hints",
            "GET /history": "periodic history snapshots",
            "GET /provider-status": "live provider mode, model, and generated-call stats",
            "GET /client/world-frame": "world-client-v1 frame for external renderers",
            "GET /report/run.json": "run report JSON",
            "GET /report/run.html": "run report HTML",
            "GET /agents": "read-only agent dossier index",
            "GET /agents/{id}": "read-only agent dossier with life journal and relationships",
            "GET /agents/{id}/social-history": "selected agent conversation history and influence chains",
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
