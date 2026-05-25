from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


EVIDENCE_GROUP_TERMS = {
    "identity": {
        "role",
        "organizer",
        "builder",
        "trader",
        "healer",
        "farmer",
        "mediator",
        "scout",
        "cook",
        "apprentice",
        "profile",
    },
    "memory": {
        "memory",
        "remembered",
        "recent",
        "reflected",
        "reflection",
        "last",
        "earlier",
        "history",
    },
    "relationship": {
        "trust",
        "relationship",
        "reconcile",
        "social",
        "faction",
        "split",
        "cooperation",
        "ties",
    },
    "organization": {
        "organization",
        "council",
        "guild",
        "cooperative",
        "household",
        "cohesion",
        "public",
    },
    "observer_intent": {
        "observer",
        "intent",
        "broadcast",
        "asked",
        "told",
        "message",
    },
    "historical_scar": {
        "crisis",
        "fracture",
        "blocked",
        "route",
        "scar",
        "hardens",
        "lasting",
        "reopened",
    },
    "resource": {
        "food",
        "materials",
        "shelter",
        "energy",
        "depot",
        "haul",
        "farm",
        "workshop",
        "logistics",
    },
    "tradeoff": {
        "but",
        "while",
        "however",
        "although",
        "outweigh",
        "balance",
        "weigh",
        "instead",
        "before",
        "against",
    },
}


@dataclass(frozen=True)
class ReasonRichnessFinding:
    day: int
    agent_id: str
    agent_name: str
    signal: str
    baseline_score: int
    generated_score: int
    baseline_groups: list[str]
    generated_groups: list[str]
    action_changed: bool
    target_changed: bool
    prompt_version: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_reason_richness(
    cognition_trace: list[dict[str, Any]],
) -> list[ReasonRichnessFinding]:
    return [
        _assess_trace_item(item)
        for item in cognition_trace
        if _is_generated_trace(item)
    ]


def _assess_trace_item(item: dict[str, Any]) -> ReasonRichnessFinding:
    baseline_plan = item.get("baseline_plan") or {}
    proposed_plan = item.get("proposed_plan") or {}
    used_plan = item.get("used_plan") or {}
    baseline_groups = _evidence_groups(baseline_plan)
    generated_groups = _evidence_groups(proposed_plan or used_plan)
    baseline_score = len(baseline_groups)
    generated_score = len(generated_groups)
    action_changed = _plan_value(baseline_plan, "action") != _plan_value(proposed_plan, "action")
    target_changed = _plan_value(baseline_plan, "target_id") != _plan_value(proposed_plan, "target_id")
    signal = _signal(
        baseline_score,
        generated_score,
        action_changed,
        target_changed,
        str(item.get("status") or ""),
    )
    return ReasonRichnessFinding(
        day=int(item.get("day", 0) or 0),
        agent_id=str(item.get("agent_id") or ""),
        agent_name=str(item.get("agent_name") or ""),
        signal=signal,
        baseline_score=baseline_score,
        generated_score=generated_score,
        baseline_groups=baseline_groups,
        generated_groups=generated_groups,
        action_changed=action_changed,
        target_changed=target_changed,
        prompt_version=str(item.get("prompt_version") or "unknown"),
        summary=_summary(
            str(item.get("agent_name") or ""),
            int(item.get("day", 0) or 0),
            signal,
            baseline_score,
            generated_score,
            generated_groups,
        ),
    )


def _is_generated_trace(item: dict[str, Any]) -> bool:
    return bool(item.get("proposed_plan"))


def _evidence_groups(plan: dict[str, Any]) -> list[str]:
    text = f"{plan.get('action', '')} {plan.get('target_id', '')} {plan.get('reason', '')}".lower()
    groups = [
        group
        for group, terms in EVIDENCE_GROUP_TERMS.items()
        if any(term in text for term in terms)
    ]
    if plan.get("target_id"):
        groups.append("specific_target")
    return _dedupe(groups)


def _signal(
    baseline_score: int,
    generated_score: int,
    action_changed: bool,
    target_changed: bool,
    status: str,
) -> str:
    if status == "fallback_after_error":
        return "reason_richness_provider_failed"
    if generated_score >= baseline_score + 2:
        if action_changed or target_changed:
            return "reason_richness_richer_with_behavior_delta"
        return "reason_richness_generated_richer"
    if generated_score <= baseline_score - 2:
        return "reason_richness_baseline_richer"
    return "reason_richness_near_tie"


def _summary(
    agent_name: str,
    day: int,
    signal: str,
    baseline_score: int,
    generated_score: int,
    generated_groups: list[str],
) -> str:
    groups = ", ".join(generated_groups) or "none"
    return (
        f"{agent_name} day {day} reason richness {signal}: "
        f"generated score {generated_score} vs baseline {baseline_score}; "
        f"generated evidence groups: {groups}."
    )


def _plan_value(plan: dict[str, Any], key: str) -> str | None:
    value = plan.get(key)
    return str(value) if value is not None else None


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
