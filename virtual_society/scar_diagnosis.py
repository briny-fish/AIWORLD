from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from .model import Agent, Event, WorldState


@dataclass(frozen=True)
class ScarBottleneck:
    kind: str
    subject: str
    status: str
    severity: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    next_step: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_scar_bottlenecks(
    world: WorldState,
    cognition_trace: list[dict[str, Any]] | None = None,
) -> list[ScarBottleneck]:
    """Explain why active historical scars remain unresolved."""

    trace = cognition_trace or []
    items: list[ScarBottleneck] = []
    items.extend(_relationship_bottlenecks(world, trace))
    items.extend(_route_bottlenecks(world))
    return items


def _relationship_bottlenecks(
    world: WorldState,
    cognition_trace: list[dict[str, Any]],
) -> list[ScarBottleneck]:
    agents_by_id = {agent.id: agent for agent in world.agents}
    items: list[ScarBottleneck] = []
    for pair_key, started_day in sorted(world.relationship_crises.items()):
        first_id, second_id = pair_key.split("|", 1)
        first = agents_by_id.get(first_id)
        second = agents_by_id.get(second_id)
        if first is None or second is None:
            continue

        trust = _average_pair_trust(first, second)
        gap = max(0.0, world.rules.relationship_repair_threshold - trust)
        direct_contacts = [
            event
            for event in world.event_log
            if event.day >= started_day
            and event.kind in {"social", "dialogue", "reconciliation"}
            and _mentions_pair(event, first, second)
        ]
        generated_social = [
            item
            for item in cognition_trace
            if int(item.get("day", -1)) >= started_day
            and str(item.get("agent_id", "")) in {first.id, second.id}
            and (item.get("used_plan") or {}).get("action") == "socialize"
        ]
        days_open = max(0, world.day - started_day + 1)

        if gap <= 0.0:
            status = "ready_but_unreconciled"
            severity = "info"
            next_step = "Run one more direct social contact so Simulation Core can emit reconciliation."
        elif not direct_contacts:
            status = "no_direct_social_repair"
            severity = "warning"
            next_step = "Create or select social actions between the pair; passive trust drift cannot clear a crisis."
        elif gap > 0.0:
            status = "repair_below_threshold"
            severity = "warning"
            next_step = "Repeat direct social repair or lower pressure elsewhere until trust crosses the repair threshold."
        else:
            status = "relationship_review_needed"
            severity = "info"
            next_step = "Inspect relationship events for this pair."

        evidence = [
            f"started day {started_day}; open {days_open} days",
            f"average trust {trust:.3f}; repair threshold {world.rules.relationship_repair_threshold:.3f}",
            f"direct contacts after crisis {len(direct_contacts)}",
            f"generated social plans after crisis {len(generated_social)}",
        ]
        if direct_contacts:
            evidence.append(f"latest contact: day {direct_contacts[-1].day} {direct_contacts[-1].kind}")

        items.append(
            ScarBottleneck(
                kind="relationship_crisis",
                subject=f"{first.name} / {second.name}",
                status=status,
                severity=severity,
                summary=_relationship_summary(first, second, trust, gap),
                evidence=evidence,
                next_step=next_step,
                metrics={
                    "pair_key": pair_key,
                    "agent_ids": [first.id, second.id],
                    "agent_names": [first.name, second.name],
                    "started_day": started_day,
                    "days_open": days_open,
                    "average_trust": round(trust, 3),
                    "repair_threshold": round(world.rules.relationship_repair_threshold, 3),
                    "trust_gap": round(gap, 3),
                    "direct_contacts": len(direct_contacts),
                    "generated_social_plans": len(generated_social),
                },
            )
        )
    return items


def _relationship_summary(first: Agent, second: Agent, trust: float, gap: float) -> str:
    if gap <= 0.0:
        return (
            f"{first.name} and {second.name} are still marked in crisis even "
            f"though trust is {trust:.3f}, at or above the repair threshold."
        )
    return (
        f"{first.name} and {second.name} remain in crisis with "
        f"{gap:.3f} trust still needed for reconciliation."
    )


def _route_bottlenecks(world: WorldState) -> list[ScarBottleneck]:
    items: list[ScarBottleneck] = []
    if not world.blocked_routes:
        return items

    locations = {location.id: location for location in world.locations}
    workshop = locations.get("workshop")
    workshop_materials = 0.0
    if workshop is not None:
        workshop_materials = workshop.resources.get("materials", 0.0)
    cohesion = _average_cohesion(world)
    progress = world.rules.route_repair_progress * (0.65 + cohesion)

    for route_key, repair_need in sorted(world.blocked_routes.items()):
        start_day = _first_route_event_day(world.event_log, route_key, "route_blocked")
        repair_events = _route_events_after(world.event_log, route_key, start_day, "route_repair")
        reopen_events = _route_events_after(world.event_log, route_key, start_day, "route_reopened")
        parts = route_key.split("|")
        conditions = [
            locations[location_id].condition
            for location_id in parts
            if location_id in locations
        ]
        min_condition = min(conditions) if conditions else 0.0
        cycles_remaining = math.ceil(repair_need / progress) if progress > 0 else 0
        materials_needed = cycles_remaining * world.rules.route_repair_material_cost

        if workshop_materials <= 0.05:
            status = "material_starved"
            severity = "critical"
            next_step = "Move or generate materials into the workshop before expecting route repair to progress."
        elif cohesion < 0.45:
            status = "cohesion_blocked"
            severity = "critical"
            next_step = "Repair institutional cohesion before common crews can work on blocked routes."
        elif not repair_events and not reopen_events:
            status = "no_repair_cycle_seen"
            severity = "warning"
            next_step = "Make repair actions explicit enough to feed workshop materials and common repair crews."
        elif cycles_remaining > 1:
            status = "repair_backlog_remaining"
            severity = "warning"
            next_step = "Keep repair pressure active for multiple days; this route is not one cycle from reopening."
        else:
            status = "near_reopen"
            severity = "info"
            next_step = "One successful repair cycle should reopen the route if materials and cohesion remain available."

        evidence = [
            f"repair need {repair_need:.3f}; estimated cycles remaining {cycles_remaining}",
            f"workshop materials {workshop_materials:.3f}; estimated materials needed {materials_needed:.3f}",
            f"institutional cohesion {cohesion:.3f}; repair floor 0.450",
            f"minimum endpoint condition {min_condition:.3f}",
            f"route repair events after block {len(repair_events)}; reopen events {len(reopen_events)}",
        ]
        if start_day >= 0:
            evidence.insert(0, f"blocked since day {start_day}")

        items.append(
            ScarBottleneck(
                kind="blocked_route",
                subject=route_key,
                status=status,
                severity=severity,
                summary=(
                    f"Route {route_key} remains blocked with {repair_need:.3f} "
                    f"repair need and {workshop_materials:.3f} workshop materials."
                ),
                evidence=evidence,
                next_step=next_step,
                metrics={
                    "route": route_key,
                    "started_day": start_day if start_day >= 0 else None,
                    "repair_need": round(repair_need, 3),
                    "estimated_cycles_remaining": cycles_remaining,
                    "estimated_materials_needed": round(materials_needed, 3),
                    "workshop_materials": round(workshop_materials, 3),
                    "institutional_cohesion": round(cohesion, 3),
                    "minimum_endpoint_condition": round(min_condition, 3),
                    "route_repair_events_after_block": len(repair_events),
                    "route_reopened_events_after_block": len(reopen_events),
                },
            )
        )
    return items


def _average_pair_trust(first: Agent, second: Agent) -> float:
    return (
        first.relationships.get(second.id, 0.50)
        + second.relationships.get(first.id, 0.50)
    ) / 2


def _mentions_pair(event: Event, first: Agent, second: Agent) -> bool:
    description = event.description.lower()
    first_name = first.name.lower()
    second_name = second.name.lower()
    if first_name in description and second_name in description:
        return True
    if event.actor_id == first.id and second_name in description:
        return True
    if event.actor_id == second.id and first_name in description:
        return True
    return False


def _average_cohesion(world: WorldState) -> float:
    if not world.organizations:
        return 0.0
    return sum(organization.cohesion for organization in world.organizations) / len(world.organizations)


def _first_route_event_day(events: list[Event], route_key: str, kind: str) -> int:
    days = [
        event.day
        for event in events
        if event.kind == kind and route_key.lower() in event.description.lower()
    ]
    return min(days) if days else -1


def _route_events_after(
    events: list[Event],
    route_key: str,
    start_day: int,
    kind: str,
) -> list[Event]:
    return [
        event
        for event in events
        if event.kind == kind
        and event.day >= max(0, start_day)
        and (kind == "route_repair" or route_key.lower() in event.description.lower())
    ]
