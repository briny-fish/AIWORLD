from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .generative_memory import memory_dicts, retrieve_memories
from .model import Action, Agent, Plan, WorldState


PLAN_PROMPT_VERSION = "cognition-plan-v3-social-pressure"

COMPACT_RULE_KEYS = {
    "exhaustion_work_threshold",
    "food_per_agent",
    "shelter_safety_ratio",
    "haul_capacity",
    "route_base_energy_cost",
    "route_hop_energy_cost",
    "route_block_condition_threshold",
    "route_repair_material_cost",
    "route_repair_progress",
    "relationship_crisis_threshold",
    "relationship_repair_threshold",
    "organization_fracture_threshold",
}

OBSERVER_ONLY_RULE_KEYS = {
    "observer_mediation_trust_gain",
}


@dataclass(frozen=True)
class CognitionContext:
    prompt_version: str
    agent: dict[str, Any]
    world: dict[str, Any]
    recent_events: list[dict[str, Any]]
    memories: list[str]
    retrieved_memories: list[dict[str, Any]]
    allowed_actions: list[str]
    baseline_plan: dict[str, Any] | None = None
    decision_pressure: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlanParseError(ValueError):
    pass


def build_cognition_context(
    agent: Agent,
    world: WorldState,
    event_limit: int = 12,
    memory_limit: int = 8,
    baseline_plan: Plan | None = None,
    compact: bool = False,
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
    retrieved_memory_dicts = memory_dicts(retrieved)
    if compact:
        retrieved_memory_dicts = _compact_retrieved_memories(retrieved_memory_dicts)

    return CognitionContext(
        prompt_version=PLAN_PROMPT_VERSION,
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
            "rules": _rules_dict(world, compact),
            "locations": [
                _location_dict(location, compact)
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
        retrieved_memories=retrieved_memory_dicts,
        allowed_actions=[action.value for action in Action],
        baseline_plan=_plan_dict(baseline_plan) if baseline_plan is not None else None,
        decision_pressure=_decision_pressure(agent, world, baseline_plan),
    )


def render_plan_prompt(context: CognitionContext) -> str:
    payload = json.dumps(context.as_dict(), ensure_ascii=False, indent=2)
    return (
        "You are a cognition module for a deterministic virtual society.\n"
        f"Prompt version: {context.prompt_version}.\n"
        "Return exactly one JSON object with keys: action, priority, reason, "
        "target_id, horizon_days.\n"
        "The action must be one of the allowed_actions. Do not invent world facts.\n"
        "Use target_id only for socialize plans; otherwise set target_id to null.\n"
        "If baseline_plan is present, treat it as the deterministic rule baseline: "
        "you may follow it or diverge, but the reason must cite concrete evidence "
        "from needs, memories, reflections, events, resources, or decision_pressure.\n"
        "Do not choose rest only because energy is imperfect. Rest only when energy "
        "is at or near the exhaustion threshold, recent work was blocked by "
        "exhaustion, or rest clearly protects later shared outcomes. Under food, "
        "material, shelter, or shock pressure, weigh personal recovery against "
        "shared production and repair needs. Active relationship crises, "
        "organization fractures, and remembered observer intents are real "
        "decision evidence; when choosing socialize, use a concrete target_id "
        "from active_relationship_crises or weakest_relationships.\n"
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

    target_id = _normalize_target_id(data.get("target_id"))
    if action != Action.SOCIALIZE:
        target_id = None

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


def _rules_dict(world: WorldState, compact: bool) -> dict[str, Any]:
    rules = {
        key: value
        for key, value in asdict(world.rules).items()
        if key not in OBSERVER_ONLY_RULE_KEYS
    }
    if not compact:
        return rules
    return {
        key: value
        for key, value in rules.items()
        if key in COMPACT_RULE_KEYS
    }


def _location_dict(location: Any, compact: bool) -> dict[str, Any]:
    base = {
        "id": location.id,
        "name": location.name,
        "kind": location.kind,
        "condition": round(location.condition, 3),
        "resources": {
            key: round(value, 3)
            for key, value in location.resources.items()
        },
        "connected_location_ids": list(location.connected_location_ids),
    }
    if compact:
        return base
    return {
        **base,
        "capacity": location.capacity,
        "production": {
            key: round(value, 3)
            for key, value in location.production.items()
        },
        "maintenance_need": round(location.maintenance_need, 3),
    }


def _compact_retrieved_memories(
    memories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    compacted = []
    for memory in memories:
        compacted.append(
            {
                "day": memory.get("day"),
                "kind": memory.get("kind"),
                "text": memory.get("text"),
                "importance": memory.get("importance"),
                "actor_id": memory.get("actor_id"),
            }
        )
    return compacted


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


def _decision_pressure(
    agent: Agent,
    world: WorldState,
    baseline_plan: Plan | None,
) -> dict[str, Any]:
    food_pressure = world.population * world.rules.food_per_agent * 1.15
    food_gap = max(0.0, food_pressure - world.resources.get("food", 0.0))
    material_floor = world.population * 0.35
    material_gap = max(0.0, material_floor - world.resources.get("materials", 0.0))
    shelter_floor = world.population * world.rules.shelter_safety_ratio
    shelter_gap = max(0.0, shelter_floor - world.resources.get("shelter", 0.0))
    energy_margin = agent.needs.energy - world.rules.exhaustion_work_threshold
    recent_plan_text = " ".join(agent.plan_history[-4:]).lower()
    recent_exhaustion_block = "blocked by exhaustion" in recent_plan_text
    active_relationship_crises = _active_relationship_crises(agent, world)
    weakest_relationships = _weakest_relationships(agent, world)
    organization_pressures = _organization_pressures(agent, world)
    remembered_observer_intents = _remembered_observer_intents(agent, world)
    blocked_routes = _blocked_routes(world)

    pressures: list[str] = []
    if food_gap > 0:
        pressures.append("shared food stores are below pressure threshold")
    if material_gap > 0:
        pressures.append("shared materials are below pressure threshold")
    if shelter_gap > 0:
        pressures.append("shared shelter is below safety floor")
    if any(event.kind == "disaster" for event in world.event_log[-10:]):
        pressures.append("recent disaster remains socially salient")
    if active_relationship_crises:
        pressures.append("agent is in active relationship crises that require direct social repair")
    if any(item["cohesion"] < 0.50 or item["fractured"] for item in organization_pressures):
        pressures.append("agent organizations show weak cohesion or fracture pressure")
    if remembered_observer_intents:
        pressures.append("agent remembers recent observer intent")
    if blocked_routes:
        pressures.append("blocked routes create persistent logistics and repair pressure")
    if not pressures:
        pressures.append("no severe shared resource pressure detected")

    guidance = [
        "baseline_plan is the plan deterministic cognition would use now",
        "diverge only when agent-local evidence or social pressure justifies it",
        "productive or repair actions matter more when resource gaps are active",
        "socialize can be justified by active relationship crises or organization fracture risk",
        "rest is justified by near-threshold energy or recent exhaustion blocks",
    ]

    return {
        "baseline_action": baseline_plan.action.value if baseline_plan else None,
        "baseline_reason": baseline_plan.reason if baseline_plan else None,
        "food_pressure_threshold": round(food_pressure, 3),
        "food_gap": round(food_gap, 3),
        "material_gap": round(material_gap, 3),
        "shelter_gap": round(shelter_gap, 3),
        "energy": round(agent.needs.energy, 3),
        "exhaustion_threshold": round(world.rules.exhaustion_work_threshold, 3),
        "energy_margin": round(energy_margin, 3),
        "near_exhaustion": energy_margin <= 0.05,
        "recent_exhaustion_block": recent_exhaustion_block,
        "active_relationship_crises": active_relationship_crises,
        "weakest_relationships": weakest_relationships,
        "organization_pressures": organization_pressures,
        "remembered_observer_intents": remembered_observer_intents,
        "blocked_routes": blocked_routes,
        "shared_pressures": pressures,
        "guidance": guidance,
    }


def _active_relationship_crises(
    agent: Agent,
    world: WorldState,
    limit: int = 5,
) -> list[dict[str, Any]]:
    crises = []
    for pair_key, started_day in sorted(world.relationship_crises.items()):
        pair = pair_key.split("|")
        if len(pair) != 2 or agent.id not in pair:
            continue
        other_id = pair[1] if pair[0] == agent.id else pair[0]
        other = _find_agent(world, other_id)
        trust = _pair_trust(agent, other)
        crises.append(
            {
                "other_agent_id": other_id,
                "other_agent_name": other.name if other is not None else other_id,
                "started_day": started_day,
                "trust": round(trust, 3),
            }
        )
    return sorted(crises, key=lambda item: (item["trust"], item["started_day"]))[:limit]


def _weakest_relationships(
    agent: Agent,
    world: WorldState,
    limit: int = 5,
) -> list[dict[str, Any]]:
    relationships = []
    for other_id, trust in agent.relationships.items():
        other = _find_agent(world, other_id)
        pair_key = _relationship_key(agent.id, other_id)
        relationships.append(
            {
                "agent_id": other_id,
                "agent_name": other.name if other is not None else other_id,
                "trust": round(trust, 3),
                "in_crisis": pair_key in world.relationship_crises,
            }
        )
    return sorted(relationships, key=lambda item: (item["trust"], item["agent_id"]))[:limit]


def _organization_pressures(agent: Agent, world: WorldState) -> list[dict[str, Any]]:
    pressures = []
    for organization in world.organizations:
        if organization.id not in agent.organization_ids:
            continue
        fractured_day = world.organization_fractures.get(organization.id)
        pressures.append(
            {
                "id": organization.id,
                "name": organization.name,
                "cohesion": round(organization.cohesion, 3),
                "fractured": fractured_day is not None or "splinter" in organization.id,
                "fractured_day": fractured_day,
                "member_count": len(organization.members),
                "norms": list(organization.norms[:4]),
            }
        )
    return sorted(pressures, key=lambda item: (item["cohesion"], item["id"]))


def _remembered_observer_intents(
    agent: Agent,
    world: WorldState,
    horizon_days: int = 7,
    limit: int = 5,
) -> list[dict[str, Any]]:
    intents = []
    for event in world.event_log:
        if event.kind != "broadcast":
            continue
        if world.day < event.day or world.day - event.day > horizon_days:
            continue
        if not any(
            memory.day == event.day
            and memory.kind == event.kind
            and memory.text == event.description
            for memory in agent.memory_stream
        ):
            continue
        intent = _intent_from_event(event)
        if not intent:
            continue
        intents.append(
            {
                "day": event.day,
                "intent": intent,
                "description": event.description,
            }
        )
    return intents[-limit:]


def _blocked_routes(
    world: WorldState,
    limit: int = 8,
) -> list[dict[str, Any]]:
    return [
        {
            "route": route_key,
            "repair_need": round(repair_need, 3),
        }
        for route_key, repair_need in sorted(world.blocked_routes.items())[:limit]
    ]


def _intent_from_event(event: Any) -> str:
    for key in event.effects:
        if key.startswith("intent_"):
            return key.removeprefix("intent_")
    return ""


def _pair_trust(agent: Agent, other: Agent | None) -> float:
    if other is None:
        return 0.50
    return (
        agent.relationships.get(other.id, 0.50)
        + other.relationships.get(agent.id, 0.50)
    ) / 2


def _find_agent(world: WorldState, agent_id: str) -> Agent | None:
    for candidate in world.agents:
        if candidate.id == agent_id:
            return candidate
    return None


def _relationship_key(first_id: str, second_id: str) -> str:
    return "|".join(sorted([first_id, second_id]))


def _plan_dict(plan: Plan) -> dict[str, Any]:
    return {
        "action": plan.action.value,
        "priority": plan.priority,
        "reason": plan.reason,
        "target_id": plan.target_id,
        "horizon_days": plan.horizon_days,
    }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_target_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "self"}:
        return None
    return text
