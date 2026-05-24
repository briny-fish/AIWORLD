from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .model import Event, Metrics, WorldState


SIGNIFICANT_EVENT_KINDS = {
    "arrival",
    "broadcast",
    "disaster",
    "dialogue",
    "edict",
    "hunger_crisis",
    "institutional_crisis",
    "intervention",
    "exchange",
    "logistics",
    "market",
    "maintenance",
    "norm_warning",
    "organization",
    "organization_fracture",
    "rationing",
    "reflection",
    "relationship_crisis",
    "reconciliation",
    "route_blocked",
    "route_reopened",
    "route_strain",
    "safety_crisis",
}


class HistoryRecorder:
    """Collects periodic read-only snapshots during a simulation run."""

    def __init__(self, seed: int, interval_days: int = 30) -> None:
        if interval_days < 1:
            raise ValueError("interval_days must be >= 1")
        self.seed = seed
        self.interval_days = interval_days
        self.snapshots: list[dict[str, Any]] = []
        self._last_event_index = 0
        self._previous_metric: Metrics | None = None

    def capture(
        self,
        world: WorldState,
        metric: Metrics,
        force: bool = False,
    ) -> None:
        if not force and not self._should_capture(metric.day):
            return
        if self.snapshots and self.snapshots[-1]["day"] == metric.day:
            return

        events = world.event_log[self._last_event_index:]
        snapshot = build_history_snapshot(
            seed=self.seed,
            world=world,
            metric=metric,
            events=events,
            previous_metric=self._previous_metric,
        )
        self.snapshots.append(snapshot)
        self._last_event_index = len(world.event_log)
        self._previous_metric = metric

    def record(self, metrics: list[Metrics]) -> dict[str, Any]:
        return build_history_record(
            seed=self.seed,
            interval_days=self.interval_days,
            snapshots=self.snapshots,
            metrics=metrics,
        )

    def _should_capture(self, day: int) -> bool:
        return day == 1 or day % self.interval_days == 0


def build_history_snapshot(
    seed: int,
    world: WorldState,
    metric: Metrics,
    events: list[Event],
    previous_metric: Metrics | None = None,
) -> dict[str, Any]:
    event_counts = Counter(event.kind for event in events)
    plan_counts = Counter(
        agent.active_plan.action.value
        for agent in world.agents
        if agent.active_plan is not None
    )
    low_need_agents = sorted(
        (
            {
                "id": agent.id,
                "name": agent.name,
                "average_need": round(agent.needs.average(), 3),
                "location_id": agent.location_id,
                "active_plan": agent.active_plan.action.value if agent.active_plan else None,
                "latest_reflection": agent.reflections[-1] if agent.reflections else None,
            }
            for agent in world.agents
            if agent.needs.average() < 0.50
        ),
        key=lambda item: item["average_need"],
    )
    significant_events = [
        {
            "day": event.day,
            "kind": event.kind,
            "actor_id": event.actor_id,
            "description": event.description,
            "effects": dict(event.effects),
        }
        for event in events
        if event.kind in SIGNIFICANT_EVENT_KINDS
    ][-12:]
    organizations = [
        {
            "id": organization.id,
            "name": organization.name,
            "kind": organization.kind,
            "home_location_id": organization.home_location_id,
            "members": list(organization.members),
            "norms": list(organization.norms),
            "inventory_targets": {
                key: round(value, 3)
                for key, value in organization.inventory_targets.items()
            },
            "exchange_preferences": {
                key: round(value, 3)
                for key, value in organization.exchange_preferences.items()
            },
            "cohesion": round(organization.cohesion, 3),
            "reputation": round(organization.reputation, 3),
        }
        for organization in world.organizations
    ]
    locations = [
        {
            "id": location.id,
            "name": location.name,
            "kind": location.kind,
            "condition": round(location.condition, 3),
            "capacity": location.capacity,
            "production": {
                key: round(value, 3)
                for key, value in location.production.items()
            },
            "maintenance_need": round(location.maintenance_need, 3),
            "resources": {
                key: round(value, 3)
                for key, value in location.resources.items()
            },
        }
        for location in world.locations
    ]
    trends = _metric_deltas(previous_metric, metric)

    return {
        "seed": seed,
        "day": metric.day,
        "summary": _snapshot_summary(metric, event_counts, trends),
        "metrics": asdict(metric),
        "trends": trends,
        "resources": {
            key: round(value, 3)
            for key, value in world.resources.items()
        },
        "relationship_crises": dict(sorted(world.relationship_crises.items())),
        "blocked_routes": {
            key: round(value, 3)
            for key, value in sorted(world.blocked_routes.items())
        },
        "organization_fractures": dict(sorted(world.organization_fractures.items())),
        "route_loads": {
            key: round(value, 3)
            for key, value in world.route_loads.items()
        },
        "event_counts": dict(sorted(event_counts.items())),
        "plan_counts": dict(sorted(plan_counts.items())),
        "low_need_agents": low_need_agents[:6],
        "organizations": organizations,
        "locations": locations,
        "significant_events": significant_events,
    }


def build_history_record(
    seed: int,
    interval_days: int,
    snapshots: list[dict[str, Any]],
    metrics: list[Metrics],
) -> dict[str, Any]:
    return {
        "kind": "history",
        "seed": seed,
        "interval_days": interval_days,
        "snapshot_count": len(snapshots),
        "summary": summarize_history(snapshots, metrics),
        "snapshots": snapshots,
    }


def summarize_history(snapshots: list[dict[str, Any]], metrics: list[Metrics]) -> str:
    if not metrics:
        return "No simulated history was recorded."
    first = metrics[0]
    final = metrics[-1]
    crisis_delta = final.crisis_events - first.crisis_events
    parts = [
        f"Day {first.day} to {final.day}",
        f"population {first.population} -> {final.population}",
        f"average need {first.average_need:.3f} -> {final.average_need:.3f}",
        f"trust {first.average_trust:.3f} -> {final.average_trust:.3f}",
        f"institutional cohesion {first.institutional_cohesion:.3f} -> {final.institutional_cohesion:.3f}",
        f"new crisis events {crisis_delta}",
    ]
    if snapshots:
        total_rationing = sum(
            int(snapshot["event_counts"].get("rationing", 0))
            for snapshot in snapshots
        )
        total_organizations = max(
            len(snapshot.get("organizations", []))
            for snapshot in snapshots
        )
        average_location_condition = _average_location_condition(snapshots[-1])
        active_relationship_crises = len(snapshots[-1].get("relationship_crises", {}))
        blocked_routes = len(snapshots[-1].get("blocked_routes", {}))
        parts.append(f"rationing events {total_rationing}")
        parts.append(f"organizations observed {total_organizations}")
        parts.append(f"average location condition {average_location_condition:.3f}")
        parts.append(f"active relationship crises {active_relationship_crises}")
        parts.append(f"blocked routes {blocked_routes}")
    return "; ".join(parts) + "."


def _average_location_condition(snapshot: dict[str, Any]) -> float:
    locations = snapshot.get("locations", [])
    if not locations:
        return 0.0
    return sum(float(location["condition"]) for location in locations) / len(locations)


def write_snapshot_files(path: str | Path, snapshots: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    for snapshot in snapshots:
        filename = f"day-{snapshot['day']:04d}.json"
        (target / filename).write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _metric_deltas(previous: Metrics | None, current: Metrics) -> dict[str, float]:
    if previous is None:
        return {
            "average_need": 0.0,
            "average_trust": 0.0,
            "average_reputation": 0.0,
            "institutional_cohesion": 0.0,
            "food": 0.0,
            "materials": 0.0,
            "shelter": 0.0,
            "crisis_events": 0.0,
        }
    return {
        "average_need": round(current.average_need - previous.average_need, 3),
        "average_trust": round(current.average_trust - previous.average_trust, 3),
        "average_reputation": round(current.average_reputation - previous.average_reputation, 3),
        "institutional_cohesion": round(
            current.institutional_cohesion - previous.institutional_cohesion,
            3,
        ),
        "food": round(current.food - previous.food, 3),
        "materials": round(current.materials - previous.materials, 3),
        "shelter": round(current.shelter - previous.shelter, 3),
        "crisis_events": float(current.crisis_events - previous.crisis_events),
    }


def _snapshot_summary(
    metric: Metrics,
    event_counts: Counter[str],
    trends: dict[str, float],
) -> str:
    total_crises = (
        event_counts.get("hunger_crisis", 0)
        + event_counts.get("safety_crisis", 0)
        + event_counts.get("institutional_crisis", 0)
        + event_counts.get("relationship_crisis", 0)
        + event_counts.get("organization_fracture", 0)
        + event_counts.get("route_blocked", 0)
    )
    trend_text = _trend_word(trends["average_need"])
    if total_crises:
        pressure = f"{total_crises} crisis events"
    elif event_counts.get("rationing", 0):
        pressure = f"{event_counts['rationing']} rationing events"
    else:
        pressure = "no crisis events"
    return (
        f"Day {metric.day}: population {metric.population}, "
        f"average need {metric.average_need:.3f} ({trend_text}), "
        f"trust {metric.average_trust:.3f}, "
        f"institutional cohesion {metric.institutional_cohesion:.3f}, "
        f"{pressure}."
    )


def _trend_word(delta: float) -> str:
    if delta > 0.025:
        return "improving"
    if delta < -0.025:
        return "declining"
    return "steady"
