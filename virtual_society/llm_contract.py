from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .generative_memory import memory_dicts, retrieve_memories
from .model import Action, Agent, Plan, WorldState


@dataclass(frozen=True)
class CognitionContext:
    agent: dict[str, Any]
    world: dict[str, Any]
    recent_events: list[dict[str, Any]]
    memories: list[str]
    retrieved_memories: list[dict[str, Any]]
    allowed_actions: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlanParseError(ValueError):
    pass


def build_cognition_context(
    agent: Agent,
    world: WorldState,
    event_limit: int = 12,
    memory_limit: int = 8,
) -> CognitionContext:
    organizations = [
        organization
        for organization in world.organizations
        if organization.id in agent.organization_ids
    ]
    memory_query = _memory_query(agent, world)
    retrieved = retrieve_memories(
        agent,
        memory_query,
        current_day=world.day,
        limit=memory_limit,
    )
    return CognitionContext(
        agent={
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "location_id": agent.location_id,
            "profile": asdict(agent.profile),
            "needs": asdict(agent.needs),
            "skills": dict(agent.skills),
            "average_trust": _average(agent.relationships.values()),
            "reputation": round(agent.reputation, 3),
            "organization_ids": list(agent.organization_ids),
            "active_plan": asdict(agent.active_plan) if agent.active_plan is not None else None,
            "recent_plan_history": agent.plan_history[-memory_limit:],
            "recent_reflections": agent.reflections[-memory_limit:],
        },
        world={
            "day": world.day,
            "population": world.population,
            "resources": dict(world.resources),
            "route_loads": dict(world.route_loads),
            "rules": asdict(world.rules),
            "locations": [
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
                    "connected_location_ids": list(location.connected_location_ids),
                }
                for location in world.locations
            ],
            "agent_organizations": [
                {
                    "id": organization.id,
                    "name": organization.name,
                    "kind": organization.kind,
                    "home_location_id": organization.home_location_id,
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
                for organization in organizations
            ],
        },
        recent_events=[asdict(event) for event in world.event_log[-event_limit:]],
        memories=agent.memories[-memory_limit:],
        retrieved_memories=memory_dicts(retrieved),
        allowed_actions=[action.value for action in Action],
    )


def render_plan_prompt(context: CognitionContext) -> str:
    payload = json.dumps(context.as_dict(), ensure_ascii=False, indent=2)
    return (
        "You are a cognition module for a deterministic virtual society.\n"
        "Return exactly one JSON object with keys: action, priority, reason, "
        "target_id, horizon_days.\n"
        "The action must be one of the allowed_actions. Do not invent world facts.\n"
        "The simulation core will validate the plan before execution.\n\n"
        f"Context:\n{payload}"
    )


def parse_plan_response(data: dict[str, Any]) -> Plan:
    if not isinstance(data, dict):
        raise PlanParseError("Plan response must be a JSON object")

    try:
        action = Action(str(data["action"]))
    except (KeyError, ValueError) as exc:
        raise PlanParseError("Plan response contains an invalid action") from exc

    try:
        priority = float(data.get("priority", 0.5))
    except (TypeError, ValueError) as exc:
        raise PlanParseError("Plan priority must be numeric") from exc

    reason = str(data.get("reason", "")).strip()
    if not reason:
        raise PlanParseError("Plan reason is required")

    target_id = data.get("target_id")
    if target_id is not None:
        target_id = str(target_id)

    try:
        horizon_days = int(data.get("horizon_days", 1))
    except (TypeError, ValueError) as exc:
        raise PlanParseError("Plan horizon_days must be an integer") from exc

    if horizon_days < 1:
        raise PlanParseError("Plan horizon_days must be >= 1")

    return Plan(
        action=action,
        priority=_clamp(priority, 0.0, 1.0),
        reason=reason,
        target_id=target_id,
        horizon_days=horizon_days,
    )


def _average(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(items) / len(items), 3)


def _memory_query(agent: Agent, world: WorldState) -> str:
    plan_text = agent.active_plan.action.value if agent.active_plan is not None else ""
    resource_text = " ".join(
        resource
        for resource, amount in world.resources.items()
        if amount < world.population * 0.75
    )
    return " ".join(
        [
            agent.role,
            plan_text,
            resource_text,
            " ".join(agent.profile.values),
            " ".join(agent.profile.long_term_goals),
            " ".join(event.kind for event in world.event_log[-6:]),
        ]
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
