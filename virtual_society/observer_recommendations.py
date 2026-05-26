from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .model import WorldState


@dataclass(frozen=True)
class ObserverRecommendation:
    title: str
    priority: str
    rationale: str
    expected_effect: str
    intervention: dict[str, Any]
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_observer_recommendations(
    world: WorldState,
    scar_diagnosis: list[dict[str, Any]],
    limit: int = 8,
) -> list[ObserverRecommendation]:
    recommendations: list[ObserverRecommendation] = []
    next_day = max(1, world.day + 1)
    prioritized = _prioritized_scars(scar_diagnosis)
    material_starved_routes = [
        item
        for item in prioritized
        if item.get("kind") == "blocked_route"
        and item.get("status") == "material_starved"
    ]
    if material_starved_routes:
        recommendations.append(
            _material_starvation_recommendation(world, material_starved_routes, next_day)
        )

    for item in prioritized:
        if len(recommendations) >= limit:
            break
        if item in material_starved_routes:
            continue
        if item.get("kind") == "blocked_route":
            recommendation = _route_recommendation(world, item, next_day)
        elif item.get("kind") == "relationship_crisis":
            recommendation = _relationship_recommendation(world, item, next_day)
        else:
            recommendation = None
        if recommendation is not None:
            recommendations.append(recommendation)

    return recommendations


def intervention_payloads(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads = []
    for item in recommendations:
        intervention = item.get("intervention")
        if isinstance(intervention, dict):
            payloads.append(intervention)
    return payloads


def _prioritized_scars(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = {
        "material_starved": 0,
        "cohesion_blocked": 1,
        "ready_but_unreconciled": 2,
        "no_direct_social_repair": 3,
        "repair_below_threshold": 4,
        "no_repair_cycle_seen": 5,
        "repair_backlog_remaining": 6,
        "near_reopen": 7,
    }
    return sorted(
        items,
        key=lambda item: (
            rank.get(str(item.get("status", "")), 99),
            str(item.get("kind", "")),
            str(item.get("subject", "")),
        ),
    )


def _route_recommendation(
    world: WorldState,
    item: dict[str, Any],
    day: int,
) -> ObserverRecommendation | None:
    metrics = item.get("metrics") or {}
    route = str(metrics.get("route") or item.get("subject") or "")
    if not route:
        return None
    status = str(item.get("status", ""))

    if status == "material_starved":
        amount = max(2.0, float(metrics.get("estimated_materials_needed") or 0.0) + 0.5)
        intervention = {
            "day": day,
            "kind": "resource",
            "actor_id": "The_Envoy",
            "reason": f"scar diagnosis: {route} is blocked by workshop material starvation",
            "params": {
                "resource": "materials",
                "amount": round(amount, 2),
                "location_id": "workshop",
            },
        }
        return ObserverRecommendation(
            title=f"Supply workshop materials for {route}",
            priority="high",
            rationale=str(item.get("summary", "")),
            expected_effect="Common repair crews can resume route repair cycles.",
            intervention=intervention,
            evidence=list(item.get("evidence") or [])[:4],
        )

    if status == "cohesion_blocked":
        intervention = {
            "day": day,
            "kind": "broadcast",
            "actor_id": "The_Envoy",
            "reason": f"scar diagnosis: {route} repair is blocked by low institutional cohesion",
            "params": {
                "intent": "repair_institutions",
                "tone": "steady",
                "strength": 0.14,
                "message": f"Stabilize council cooperation so crews can reopen {route}.",
            },
        }
        return ObserverRecommendation(
            title=f"Stabilize institutions for {route}",
            priority="high",
            rationale=str(item.get("summary", "")),
            expected_effect="Institutional cohesion can rise enough for common crews to repair blocked routes.",
            intervention=intervention,
            evidence=list(item.get("evidence") or [])[:4],
        )

    repair_targets = _repair_agent_ids(world)
    intervention = {
        "day": day,
        "kind": "broadcast",
        "actor_id": "The_Envoy",
        "reason": f"scar diagnosis: {route} needs explicit repair pressure",
        "params": {
            "intent": "repair_routes",
            "target_agent_ids": repair_targets,
            "tone": "practical",
            "strength": 0.14,
            "message": f"Prioritize materials and repair work to reopen {route}.",
        },
    }
    return ObserverRecommendation(
        title=f"Focus repair work on {route}",
        priority="medium",
        rationale=str(item.get("summary", "")),
        expected_effect="Repair-capable agents receive a concrete memory and planning bias for this route.",
        intervention=intervention,
        evidence=list(item.get("evidence") or [])[:4],
    )


def _material_starvation_recommendation(
    world: WorldState,
    items: list[dict[str, Any]],
    day: int,
) -> ObserverRecommendation:
    routes = [str((item.get("metrics") or {}).get("route") or item.get("subject")) for item in items]
    estimated_materials = sum(
        max(0.5, float((item.get("metrics") or {}).get("estimated_materials_needed") or 0.0))
        for item in items
    )
    amount = max(2.0, min(8.0, estimated_materials + 0.5))
    intervention = {
        "day": day,
        "kind": "resource",
        "actor_id": "The_Envoy",
        "reason": f"scar diagnosis: {len(routes)} blocked routes are starved of workshop materials",
        "params": {
            "resource": "materials",
            "amount": round(amount, 2),
            "location_id": "workshop",
        },
    }
    workshop_materials = 0.0
    for location in world.locations:
        if location.id == "workshop":
            workshop_materials = location.resources.get("materials", 0.0)
            break
    return ObserverRecommendation(
        title=f"Supply workshop materials for {len(routes)} blocked routes",
        priority="high",
        rationale=(
            f"{len(routes)} blocked routes are material-starved; workshop has "
            f"{workshop_materials:.3f} materials."
        ),
        expected_effect="Common repair crews can resume route repair cycles across multiple blocked routes.",
        intervention=intervention,
        evidence=routes[:6],
    )


def _relationship_recommendation(
    world: WorldState,
    item: dict[str, Any],
    day: int,
) -> ObserverRecommendation | None:
    metrics = item.get("metrics") or {}
    agent_ids = [
        str(value)
        for value in metrics.get("agent_ids", [])
        if str(value)
    ]
    agent_names = [
        str(value)
        for value in metrics.get("agent_names", [])
        if str(value)
    ]
    if len(agent_ids) != 2:
        return None

    subject = " and ".join(agent_names) if len(agent_names) == 2 else str(item.get("subject", "the pair"))
    status = str(item.get("status", ""))
    trust_gap = float(metrics.get("trust_gap") or 0.0)
    mediation_can_clear = trust_gap <= world.rules.observer_mediation_trust_gain
    message = (
        f"{subject}, meet directly and repair trust before this crisis hardens further."
    )
    if status == "ready_but_unreconciled":
        message = f"{subject}, meet once more so the repaired trust becomes public reconciliation."

    intervention_kind = (
        "mediation"
        if status == "ready_but_unreconciled" or mediation_can_clear
        else "broadcast"
    )
    params: dict[str, Any] = {
        "target_agent_ids": agent_ids,
        "tone": "neutral",
        "message": message,
    }
    if intervention_kind == "broadcast":
        params.update({"intent": "reconcile_relationships", "strength": 0.16})
    intervention = {
        "day": day,
        "kind": intervention_kind,
        "actor_id": "The_Envoy",
        "reason": f"scar diagnosis: {subject} relationship crisis needs direct repair",
        "params": params,
    }
    priority = "high" if status == "ready_but_unreconciled" else "medium"
    expected_effect = (
        "Simulation Core schedules a bounded mediated meeting and emits reconciliation if trust is already high enough."
        if intervention_kind == "mediation"
        else "Both agents receive a targeted memory that can bias social plans toward reconciliation."
    )
    return ObserverRecommendation(
        title=f"Prompt direct reconciliation: {subject}",
        priority=priority,
        rationale=str(item.get("summary", "")),
        expected_effect=expected_effect,
        intervention=intervention,
        evidence=list(item.get("evidence") or [])[:4],
    )


def _repair_agent_ids(world: WorldState, limit: int = 3) -> list[str]:
    ranked = sorted(
        world.agents,
        key=lambda agent: (
            agent.skills.get("building", 0.0),
            agent.skills.get("logistics", 0.0),
            agent.reputation,
        ),
        reverse=True,
    )
    return [agent.id for agent in ranked[:limit]]
