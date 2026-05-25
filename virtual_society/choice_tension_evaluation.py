from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .model import Event, WorldState


ACTION_GROUPS = {
    "farm": "food",
    "haul": "logistics",
    "gather": "materials",
    "repair": "repair",
    "socialize": "social",
    "rest": "recovery",
}

INTENT_GROUPS = {
    "repair_routes": "repair",
    "reconcile_relationships": "social",
    "protect_food": "food",
    "coordinate": "social",
}

GROUP_TERMS = {
    "food": {"food", "hunger", "farm", "ration", "nutrition", "granary"},
    "logistics": {"haul", "depot", "route", "distribution", "logistics", "transport"},
    "materials": {"materials", "workshop", "gather", "tools"},
    "repair": {"repair", "blocked", "route", "reopen", "maintenance", "shelter"},
    "social": {"social", "trust", "relationship", "reconcile", "coordination"},
    "recovery": {"rest", "energy", "exhaustion", "fatigue"},
}


@dataclass(frozen=True)
class ChoiceTensionFinding:
    day: int
    agent_id: str
    agent_name: str
    signal: str
    baseline_action: str | None
    proposed_action: str | None
    used_action: str | None
    competing_groups: list[str]
    mentioned_groups: list[str]
    observer_intents: list[str]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_choice_tensions(
    world: WorldState,
    cognition_trace: list[dict[str, Any]],
    horizon_days: int = 7,
) -> list[ChoiceTensionFinding]:
    findings = []
    for item in cognition_trace:
        finding = _assess_trace_item(world, item, horizon_days)
        if finding is not None:
            findings.append(finding)
    return findings


def _assess_trace_item(
    world: WorldState,
    item: dict[str, Any],
    horizon_days: int,
) -> ChoiceTensionFinding | None:
    day = int(item.get("day", 0) or 0)
    agent_id = str(item.get("agent_id") or "")
    agent = next((candidate for candidate in world.agents if candidate.id == agent_id), None)
    if agent is None:
        return None

    baseline_plan = item.get("baseline_plan") or {}
    proposed_plan = item.get("proposed_plan") or {}
    used_plan = item.get("used_plan") or {}
    baseline_action = _plan_action(baseline_plan)
    proposed_action = _plan_action(proposed_plan)
    used_action = _plan_action(used_plan)
    observer_intents = _observer_intents_for_agent(world, agent_id, day, horizon_days)

    competing_groups = _competing_groups(
        baseline_plan,
        proposed_plan,
        observer_intents,
    )
    if len(competing_groups) < 2:
        return None

    generated_reason = str(proposed_plan.get("reason") or used_plan.get("reason") or "")
    mentioned_groups = [
        group
        for group in competing_groups
        if _mentions_group(generated_reason, group)
    ]
    signal = _signal(
        baseline_action,
        proposed_action,
        used_action,
        competing_groups,
        mentioned_groups,
        str(item.get("status") or ""),
    )
    return ChoiceTensionFinding(
        day=day,
        agent_id=agent.id,
        agent_name=agent.name,
        signal=signal,
        baseline_action=baseline_action,
        proposed_action=proposed_action,
        used_action=used_action,
        competing_groups=competing_groups,
        mentioned_groups=mentioned_groups,
        observer_intents=observer_intents,
        summary=_summary(
            agent.name,
            day,
            signal,
            baseline_action,
            used_action,
            competing_groups,
            mentioned_groups,
            observer_intents,
        ),
    )


def _observer_intents_for_agent(
    world: WorldState,
    agent_id: str,
    day: int,
    horizon_days: int,
) -> list[str]:
    agent = next((candidate for candidate in world.agents if candidate.id == agent_id), None)
    if agent is None:
        return []
    intents = []
    for event in world.event_log:
        if event.kind != "broadcast":
            continue
        if event.day > day or day - event.day > horizon_days:
            continue
        if not _agent_remembers_event(agent, event):
            continue
        intent = _intent_from_event(event)
        if intent:
            intents.append(intent)
    return list(dict.fromkeys(intents))


def _agent_remembers_event(agent: Any, event: Event) -> bool:
    return any(
        memory.day == event.day
        and memory.kind == event.kind
        and memory.text == event.description
        for memory in agent.memory_stream
    )


def _intent_from_event(event: Event) -> str:
    for key in event.effects:
        if key.startswith("intent_"):
            return key.removeprefix("intent_")
    return ""


def _competing_groups(
    baseline_plan: dict[str, Any],
    proposed_plan: dict[str, Any],
    observer_intents: list[str],
) -> list[str]:
    groups: list[str] = []
    for action in (_plan_action(baseline_plan), _plan_action(proposed_plan)):
        group = ACTION_GROUPS.get(action or "")
        if group:
            groups.append(group)

    text = f"{baseline_plan.get('reason', '')} {proposed_plan.get('reason', '')}".lower()
    for group, terms in GROUP_TERMS.items():
        if any(term in text for term in terms):
            groups.append(group)

    for intent in observer_intents:
        group = INTENT_GROUPS.get(intent)
        if group:
            groups.append(group)

    return _dedupe_preserving_order(groups)


def _mentions_group(text: str, group: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in GROUP_TERMS.get(group, set()))


def _signal(
    baseline_action: str | None,
    proposed_action: str | None,
    used_action: str | None,
    competing_groups: list[str],
    mentioned_groups: list[str],
    status: str,
) -> str:
    if status == "fallback_after_error":
        return "choice_tension_provider_failed"
    if proposed_action and proposed_action != baseline_action:
        if used_action == proposed_action:
            return "choice_tension_action_diverged"
        return "choice_tension_proposal_blocked"
    if len(mentioned_groups) >= min(2, len(competing_groups)):
        return "choice_tension_baseline_aligned_with_tradeoff"
    return "choice_tension_baseline_aligned_without_tradeoff"


def _summary(
    agent_name: str,
    day: int,
    signal: str,
    baseline_action: str | None,
    used_action: str | None,
    competing_groups: list[str],
    mentioned_groups: list[str],
    observer_intents: list[str],
) -> str:
    intent_text = (
        f" Observer intents: {', '.join(observer_intents)}."
        if observer_intents
        else ""
    )
    return (
        f"{agent_name} faced choice tension on day {day}: "
        f"baseline={baseline_action or 'none'}, used={used_action or 'none'}, "
        f"competing groups={', '.join(competing_groups)}, "
        f"mentioned={', '.join(mentioned_groups) or 'none'}, signal={signal}."
        f"{intent_text}"
    )


def _plan_action(plan: dict[str, Any]) -> str | None:
    action = plan.get("action") if plan else None
    return str(action) if action else None


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
