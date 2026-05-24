from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .model import WorldState


SCAR_EVENT_KINDS = {
    "relationship_crisis",
    "reconciliation",
    "organization_fracture",
    "route_blocked",
    "route_reopened",
}


@dataclass(frozen=True)
class HistoricalScarFinding:
    code: str
    status: str
    description: str
    value: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_historical_scar_validation(
    world: WorldState,
    history: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize whether persistent historical scars are real state.

    This is not a new social-quality evaluator. It is a compact validation gate
    for the irreversible-history substrate: scars must live in state, affect
    future mechanics, and have explicit repair paths.
    """

    history_counts = _event_counts_from_history(history)
    events = _events_from_history(history) or [
        {
            "kind": event.kind,
            "description": event.description,
            "effects": dict(event.effects),
        }
        for event in world.event_log
    ]
    event_counts = history_counts or _event_counts(events)
    findings = [
        _relationship_crisis_finding(world, event_counts),
        _organization_fracture_finding(world, event_counts),
        _blocked_route_finding(world, event_counts),
        _repair_path_finding(world, event_counts),
    ]
    active_total = (
        len(world.relationship_crises)
        + len(world.blocked_routes)
        + len(world.organization_fractures)
    )
    return {
        "summary": _validation_summary(findings, active_total),
        "active_relationship_crises": len(world.relationship_crises),
        "active_blocked_routes": len(world.blocked_routes),
        "recorded_organization_fractures": len(world.organization_fractures),
        "scar_event_counts": {
            kind: event_counts.get(kind, 0)
            for kind in sorted(SCAR_EVENT_KINDS)
        },
        "findings": [finding.as_dict() for finding in findings],
    }


def _relationship_crisis_finding(
    world: WorldState,
    event_counts: dict[str, int],
) -> HistoricalScarFinding:
    active = len(world.relationship_crises)
    recorded = event_counts.get("relationship_crisis", 0)
    repaired = event_counts.get("reconciliation", 0)
    if active:
        return HistoricalScarFinding(
            code="relationship_crises_persist",
            status="pass",
            description=(
                f"{active} relationship crises remain active and are excluded "
                "from passive trust drift until direct reconciliation."
            ),
            value=float(active),
        )
    if recorded and repaired:
        return HistoricalScarFinding(
            code="relationship_crises_repaired",
            status="pass",
            description=f"{recorded} relationship crises were recorded and {repaired} reconciliations occurred.",
            value=float(repaired),
        )
    if recorded:
        return HistoricalScarFinding(
            code="relationship_crises_cleared",
            status="info",
            description=f"{recorded} relationship crises were recorded but none remain active.",
            value=0.0,
        )
    return HistoricalScarFinding(
        code="no_relationship_crisis",
        status="info",
        description="No relationship crisis was triggered in this run.",
        value=0.0,
    )


def _organization_fracture_finding(
    world: WorldState,
    event_counts: dict[str, int],
) -> HistoricalScarFinding:
    fractures = len(world.organization_fractures)
    splinters = [
        organization
        for organization in world.organizations
        if "splinter" in organization.id or "Splinter" in organization.name
    ]
    if fractures and splinters:
        return HistoricalScarFinding(
            code="organization_fractures_persist",
            status="pass",
            description=(
                f"{fractures} organization fractures are recorded and "
                f"{len(splinters)} splinter organizations still exist."
            ),
            value=float(fractures),
        )
    if event_counts.get("organization_fracture", 0):
        return HistoricalScarFinding(
            code="organization_fractures_unverified",
            status="warning",
            description="Organization fracture events occurred, but no splinter organization is visible now.",
            value=float(event_counts["organization_fracture"]),
        )
    return HistoricalScarFinding(
        code="no_organization_fracture",
        status="info",
        description="No organization fracture was triggered in this run.",
        value=0.0,
    )


def _blocked_route_finding(
    world: WorldState,
    event_counts: dict[str, int],
) -> HistoricalScarFinding:
    active = len(world.blocked_routes)
    if active:
        invalid_routes = [
            key
            for key, repair_need in world.blocked_routes.items()
            if repair_need <= 0.0 or len(key.split("|")) != 2
        ]
        if invalid_routes:
            return HistoricalScarFinding(
                code="blocked_routes_invalid",
                status="warning",
                description=f"{len(invalid_routes)} blocked routes have invalid repair state.",
                value=float(len(invalid_routes)),
            )
        return HistoricalScarFinding(
            code="blocked_routes_affect_paths",
            status="pass",
            description=(
                f"{active} blocked routes are removed from route neighbor lookup "
                "and require repair progress before reopening."
            ),
            value=float(active),
        )
    if event_counts.get("route_blocked", 0) and event_counts.get("route_reopened", 0):
        return HistoricalScarFinding(
            code="blocked_routes_repaired",
            status="pass",
            description=(
                f"{event_counts['route_blocked']} route blockages occurred and "
                f"{event_counts['route_reopened']} reopenings were recorded."
            ),
            value=float(event_counts["route_reopened"]),
        )
    if event_counts.get("route_blocked", 0):
        return HistoricalScarFinding(
            code="blocked_routes_cleared",
            status="info",
            description=f"{event_counts['route_blocked']} route blockages were recorded but none remain active.",
            value=0.0,
        )
    return HistoricalScarFinding(
        code="no_blocked_route",
        status="info",
        description="No route blockage was triggered in this run.",
        value=0.0,
    )


def _repair_path_finding(
    world: WorldState,
    event_counts: dict[str, int],
) -> HistoricalScarFinding:
    repairs = event_counts.get("reconciliation", 0) + event_counts.get("route_reopened", 0)
    pending = len(world.relationship_crises) + len(world.blocked_routes)
    if repairs:
        return HistoricalScarFinding(
            code="repair_path_observed",
            status="pass",
            description=f"{repairs} repair events were observed across relationships or routes.",
            value=float(repairs),
        )
    if pending:
        return HistoricalScarFinding(
            code="repair_path_pending",
            status="info",
            description=(
                f"{pending} active scars remain unrepaired; this preserves a "
                "future repair target rather than silently clearing state."
            ),
            value=float(pending),
        )
    return HistoricalScarFinding(
        code="no_repair_needed",
        status="info",
        description="No active relationship or route scar needs repair.",
        value=0.0,
    )


def _validation_summary(
    findings: list[HistoricalScarFinding],
    active_total: int,
) -> str:
    warnings = [finding for finding in findings if finding.status == "warning"]
    passes = [finding for finding in findings if finding.status == "pass"]
    if warnings:
        return f"Historical scar validation found {len(warnings)} warnings across {active_total} active scars."
    if active_total:
        return f"Historical scar validation passed with {active_total} active persistent scars."
    if passes:
        return "Historical scar validation passed; scars occurred and were repaired or persisted cleanly."
    return "Historical scar validation found no active scars in this run."


def _events_from_history(history: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not history:
        return []
    events = []
    for snapshot in history.get("snapshots", []):
        events.extend(snapshot.get("significant_events", []))
    return events


def _event_counts_from_history(history: dict[str, Any] | None) -> dict[str, int]:
    if not history:
        return {}
    counts: dict[str, int] = {}
    for snapshot in history.get("snapshots", []):
        for kind, count in (snapshot.get("event_counts") or {}).items():
            counts[str(kind)] = counts.get(str(kind), 0) + int(count)
    return counts


def _event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        kind = str(event.get("kind", ""))
        counts[kind] = counts.get(kind, 0) + 1
    return counts
