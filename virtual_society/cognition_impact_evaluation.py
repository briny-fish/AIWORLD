from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .model import Action, Agent, Event, WorldState


@dataclass(frozen=True)
class CognitionExecutionEvidence:
    day: int
    agent_id: str
    agent_name: str
    kind: str
    text: str
    effects: dict[str, float]


@dataclass(frozen=True)
class CognitionPlanDelta:
    day: int
    run_plan: str
    baseline_plan: str | None
    run_action: str | None
    baseline_action: str | None
    change_kind: str


@dataclass(frozen=True)
class CognitionImpact:
    day: int
    agent_id: str
    agent_name: str
    status: str
    signal: str
    baseline_action: str | None
    proposed_action: str | None
    used_action: str | None
    proposed_diverged_from_baseline: bool
    used_diverged_from_baseline: bool
    execution_evidence: list[CognitionExecutionEvidence]
    baseline_plan_deltas: list[CognitionPlanDelta]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_cognition_impacts(
    world: WorldState,
    cognition_trace: list[dict[str, Any]],
    baseline_world: WorldState | None = None,
    plan_window_days: int = 7,
) -> list[CognitionImpact]:
    """Evaluate whether generated cognition changed executable behavior."""
    if plan_window_days < 0:
        raise ValueError("plan_window_days must be >= 0")

    impacts: list[CognitionImpact] = []
    for item in cognition_trace:
        day = int(item.get("day", 0))
        agent = _find_agent(world, str(item.get("agent_id", "")))
        if agent is None:
            continue

        baseline_plan = item.get("baseline_plan") or {}
        proposed_plan = item.get("proposed_plan") or {}
        used_plan = item.get("used_plan") or {}
        baseline_action = _plan_action_dict(baseline_plan)
        proposed_action = _plan_action_dict(proposed_plan)
        used_action = _plan_action_dict(used_plan)
        status = str(item.get("status") or "")
        proposed_diverged = _plan_dict_differs(proposed_plan, baseline_plan)
        used_diverged = _plan_dict_differs(used_plan, baseline_plan)

        baseline_agent = (
            _find_agent(baseline_world, agent.id)
            if baseline_world is not None
            else None
        )
        window_end = min(world.day, day + plan_window_days)
        execution = _execution_evidence(world, agent, day, used_action)
        deltas = _baseline_plan_deltas(agent, baseline_agent, day, window_end)
        signal = _signal(
            status,
            baseline_action,
            proposed_action,
            used_action,
            proposed_diverged,
            used_diverged,
        )
        impacts.append(
            CognitionImpact(
                day=day,
                agent_id=agent.id,
                agent_name=agent.name,
                status=status,
                signal=signal,
                baseline_action=baseline_action,
                proposed_action=proposed_action,
                used_action=used_action,
                proposed_diverged_from_baseline=proposed_diverged,
                used_diverged_from_baseline=used_diverged,
                execution_evidence=execution,
                baseline_plan_deltas=deltas,
                summary=_summary(
                    day,
                    agent.name,
                    signal,
                    baseline_action,
                    proposed_action,
                    used_action,
                    len(execution),
                    deltas,
                    baseline_world is not None,
                ),
            )
        )
    return impacts


def _find_agent(world: WorldState | None, agent_id: str) -> Agent | None:
    if world is None:
        return None
    return next((agent for agent in world.agents if agent.id == agent_id), None)


def _execution_evidence(
    world: WorldState,
    agent: Agent,
    day: int,
    action: str | None,
) -> list[CognitionExecutionEvidence]:
    if action is None:
        return []
    evidence = []
    for event in world.event_log:
        if event.day != day or event.actor_id != agent.id:
            continue
        if not _event_matches_action(event, action):
            continue
        evidence.append(
            CognitionExecutionEvidence(
                day=event.day,
                agent_id=agent.id,
                agent_name=agent.name,
                kind=event.kind,
                text=event.description,
                effects=dict(event.effects),
            )
        )
    return evidence[:6]


def _event_matches_action(event: Event, action: str) -> bool:
    text = event.description.lower()
    if action == Action.FARM.value:
        return event.kind == "work" and "farmed" in text
    if action == Action.GATHER.value:
        return event.kind == "work" and "gathered" in text
    if action == Action.REPAIR.value:
        return event.kind == "work" and "repaired" in text
    if action == Action.HAUL.value:
        return event.kind == "transport" or (
            event.kind == "rest" and "hauling route" in text
        )
    if action == Action.REST.value:
        return event.kind == "rest"
    if action == Action.SOCIALIZE.value:
        return event.kind in {"social", "dialogue"}
    return False


def _baseline_plan_deltas(
    agent: Agent,
    baseline_agent: Agent | None,
    window_start: int,
    window_end: int,
) -> list[CognitionPlanDelta]:
    if baseline_agent is None:
        return []

    run_entries = _plans_by_day(agent, window_start, window_end)
    baseline_entries = _plans_by_day(baseline_agent, window_start, window_end)
    deltas = []
    for day in sorted(set(run_entries) | set(baseline_entries)):
        run_plan = run_entries.get(day)
        baseline_plan = baseline_entries.get(day)
        if run_plan is None or run_plan == baseline_plan:
            continue
        deltas.append(
            CognitionPlanDelta(
                day=day,
                run_plan=run_plan,
                baseline_plan=baseline_plan,
                run_action=_plan_action_text(run_plan),
                baseline_action=_plan_action_text(baseline_plan),
                change_kind=_plan_change_kind(run_plan, baseline_plan),
            )
        )
    return deltas[:8]


def _plans_by_day(agent: Agent, window_start: int, window_end: int) -> dict[int, str]:
    entries = {}
    for entry in agent.plan_history:
        day = _entry_day(entry)
        if window_start <= day <= window_end:
            entries[day] = entry
    return entries


def _signal(
    status: str,
    baseline_action: str | None,
    proposed_action: str | None,
    used_action: str | None,
    proposed_diverged: bool,
    used_diverged: bool,
) -> str:
    if status == "fallback_after_error":
        return "cognition_provider_failed"
    if status == "baseline_after_policy":
        return "cognition_proposal_policy_blocked"
    if used_action is not None and used_action != baseline_action:
        return "cognition_action_diverged"
    if used_diverged:
        return "cognition_plan_context_diverged"
    if proposed_diverged:
        return "cognition_proposal_only_diverged"
    return "cognition_baseline_aligned"


def _summary(
    day: int,
    agent_name: str,
    signal: str,
    baseline_action: str | None,
    proposed_action: str | None,
    used_action: str | None,
    execution_count: int,
    deltas: list[CognitionPlanDelta],
    has_baseline: bool,
) -> str:
    action_deltas = sum(1 for item in deltas if item.change_kind == "action")
    context_deltas = len(deltas) - action_deltas
    baseline_text = "no rule baseline was supplied"
    if has_baseline and not deltas:
        baseline_text = "no baseline plan deltas were found"
    elif deltas:
        baseline_text = (
            f"{action_deltas} action deltas and {context_deltas} "
            "plan-context deltas against the rule baseline"
        )
    return (
        f"Generated cognition for {agent_name} on day {day} produced signal "
        f"{signal}; baseline={baseline_action or 'none'}, "
        f"proposed={proposed_action or 'none'}, used={used_action or 'none'}; "
        f"execution evidence {execution_count}; {baseline_text}."
    )


def _plan_dict_differs(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if not first or not second:
        return bool(first) != bool(second)
    keys = ("action", "target_id", "horizon_days", "reason")
    return any(first.get(key) != second.get(key) for key in keys)


def _plan_action_dict(plan: dict[str, Any]) -> str | None:
    value = plan.get("action") if plan else None
    return str(value) if value else None


def _entry_day(text: str) -> int:
    match = re.search(r"\bday\s+(\d+)\b", text.lower())
    return int(match.group(1)) if match is not None else 0


def _plan_action_text(text: str | None) -> str | None:
    if text is None:
        return None
    match = re.search(r"\bday\s+\d+:\s*([a-z_]+)\s*\|", text.lower())
    return match.group(1) if match is not None else None


def _plan_change_kind(run_plan: str, baseline_plan: str | None) -> str:
    if _plan_action_text(run_plan) != _plan_action_text(baseline_plan):
        return "action"
    return "context"
