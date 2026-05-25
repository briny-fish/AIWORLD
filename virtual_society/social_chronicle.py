from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ChronicleEntry:
    day: int
    title: str
    summary: str
    evidence: list[str]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_social_chronicle(
    history: dict[str, Any] | None,
    social_findings: list[dict[str, Any]] | None = None,
    observer_intents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not history or not history.get("snapshots"):
        return {
            "summary": "No history snapshots are available for a social chronicle.",
            "entries": [],
            "evaluation_signals": social_findings or [],
        }

    observer_intents = observer_intents or []
    entries = []
    previous_day = 0
    for snapshot in history.get("snapshots", []):
        day = int(snapshot.get("day", 0))
        entries.append(
            _entry_from_snapshot(
                snapshot,
                _observer_intents_for_window(observer_intents, previous_day, day),
            )
        )
        previous_day = day
    return {
        "summary": _chronicle_summary(entries, social_findings or []),
        "entries": [entry.as_dict() for entry in entries],
        "evaluation_signals": social_findings or [],
    }


def _entry_from_snapshot(
    snapshot: dict[str, Any],
    observer_intents: list[dict[str, Any]],
) -> ChronicleEntry:
    event_counts = snapshot.get("event_counts", {})
    significant_events = snapshot.get("significant_events", [])
    metrics = snapshot.get("metrics", {})
    title = _title(event_counts, observer_intents)
    evidence = _evidence_lines(snapshot, significant_events, observer_intents)
    summary = _summary(snapshot, title, evidence)
    return ChronicleEntry(
        day=int(snapshot.get("day", 0)),
        title=title,
        summary=summary,
        evidence=evidence,
        metrics={
            "average_need": metrics.get("average_need"),
            "average_trust": metrics.get("average_trust"),
            "institutional_cohesion": metrics.get("institutional_cohesion"),
            "crisis_events": metrics.get("crisis_events"),
        },
    )


def _title(
    event_counts: dict[str, Any],
    observer_intents: list[dict[str, Any]],
) -> str:
    if int(event_counts.get("organization_fracture", 0)):
        return "Institutional fracture"
    if int(event_counts.get("relationship_crisis", 0)):
        return "Relationship crisis"
    if int(event_counts.get("route_blocked", 0)):
        return "Route network scarred"
    if int(event_counts.get("route_reopened", 0)) or int(event_counts.get("reconciliation", 0)):
        return "Repair work"
    if int(event_counts.get("disaster", 0)):
        return "External shock"
    if int(event_counts.get("hunger_crisis", 0)) or int(event_counts.get("safety_crisis", 0)):
        return "Shared crisis"
    if observer_intents:
        return "Observer-influenced adaptation"
    if int(event_counts.get("dialogue", 0)) or int(event_counts.get("reflection", 0)):
        return "Social interpretation"
    return "Routine adaptation"


def _evidence_lines(
    snapshot: dict[str, Any],
    events: list[dict[str, Any]],
    observer_intents: list[dict[str, Any]],
) -> list[str]:
    event_counts = snapshot.get("event_counts", {})
    lines: list[str] = []
    lines.extend(_observer_evidence_lines(observer_intents))
    for kind, label in (
        ("relationship_crisis", "relationship crises"),
        ("reconciliation", "reconciliations"),
        ("organization_fracture", "organization fractures"),
        ("route_blocked", "route blockages"),
        ("route_reopened", "route reopenings"),
        ("hunger_crisis", "hunger crises"),
        ("safety_crisis", "safety crises"),
        ("disaster", "external shocks"),
    ):
        count = int(event_counts.get(kind, 0))
        if count:
            lines.append(f"{count} {label}")

    active_relationships = len(snapshot.get("relationship_crises", {}))
    blocked_routes = len(snapshot.get("blocked_routes", {}))
    fractures = len(snapshot.get("organization_fractures", {}))
    if active_relationships:
        lines.append(f"{active_relationships} active relationship scars")
    if blocked_routes:
        lines.append(f"{blocked_routes} blocked routes still constrain movement")
    if fractures:
        lines.append(f"{fractures} recorded organization fractures")

    examples = [
        str(event.get("description", "")).rstrip(".")
        for event in events
        if event.get("kind")
        in {
            "relationship_crisis",
            "reconciliation",
            "organization_fracture",
            "route_blocked",
            "route_reopened",
            "disaster",
        }
    ][-2:]
    lines.extend(examples)
    return lines[:6]


def _observer_intents_for_window(
    observer_intents: list[dict[str, Any]],
    previous_day: int,
    day: int,
) -> list[dict[str, Any]]:
    return [
        item
        for item in observer_intents
        if previous_day < int(item.get("day", 0)) <= day
    ]


def _observer_evidence_lines(observer_intents: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in observer_intents[-3:]:
        intent = str(item.get("intent", "observer")).replace("_", " ")
        targets = [str(value) for value in item.get("target_agents") or []]
        target_text = _target_text(targets)
        plan_hits = int(item.get("plan_hits", 0) or 0)
        memory_hits = int(item.get("memory_hits", 0) or 0)
        signal = str(item.get("signal", ""))
        if signal == "intent_memory_plan_echo":
            lines.append(
                f"observer intent {intent} reached {target_text}; "
                f"{plan_hits} plans echoed it"
            )
        elif memory_hits:
            lines.append(
                f"observer intent {intent} became shared memory for "
                f"{memory_hits} targeted agents"
            )
        else:
            lines.append(f"observer intent {intent} was broadcast")
    return lines


def _target_text(targets: list[str]) -> str:
    if not targets:
        return "targeted agents"
    if len(targets) <= 4:
        return ", ".join(targets)
    return f"{', '.join(targets[:4])}, +{len(targets) - 4} more"


def _summary(
    snapshot: dict[str, Any],
    title: str,
    evidence: list[str],
) -> str:
    metrics = snapshot.get("metrics", {})
    trends = snapshot.get("trends", {})
    day = snapshot.get("day", 0)
    need = metrics.get("average_need", 0)
    trust = metrics.get("average_trust", 0)
    cohesion = metrics.get("institutional_cohesion", 0)
    direction = _direction(float(trends.get("average_need", 0.0)))
    if evidence:
        evidence_text = "; ".join(evidence[:3])
        return (
            f"Day {day}: {title.lower()} shaped the society while need {direction} "
            f"to {need}, trust was {trust}, and cohesion was {cohesion}. "
            f"Evidence: {evidence_text}."
        )
    return (
        f"Day {day}: {title.lower()} continued with average need {need}, "
        f"trust {trust}, and cohesion {cohesion}."
    )


def _chronicle_summary(
    entries: list[ChronicleEntry],
    social_findings: list[dict[str, Any]],
) -> str:
    if not entries:
        return "No social chronicle entries were produced."
    scar_entries = sum(
        1
        for entry in entries
        if entry.title
        in {
            "Institutional fracture",
            "Relationship crisis",
            "Route network scarred",
            "Repair work",
        }
    )
    signals = ", ".join(
        str(item.get("code"))
        for item in social_findings[:3]
        if item.get("code")
    )
    observer_entries = sum(
        1
        for entry in entries
        if any("observer intent" in evidence for evidence in entry.evidence)
    )
    observer_suffix = (
        f" {observer_entries} entries include observer impact."
        if observer_entries
        else ""
    )
    suffix = f" Evaluation signals: {signals}." if signals else ""
    return (
        f"Chronicle produced {len(entries)} entries; "
        f"{scar_entries} entries reference persistent scars."
        f"{observer_suffix}{suffix}"
    )


def _direction(delta: float) -> str:
    if delta > 0.025:
        return "improved"
    if delta < -0.025:
        return "declined"
    return "held steady"
