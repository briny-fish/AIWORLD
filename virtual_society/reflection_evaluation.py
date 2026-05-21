from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .model import Agent, Event, WorldState


FOCUS_TERMS = {
    "shock": {"damage", "damaged", "disaster", "haul", "repair", "shock", "storm"},
    "social": {"care", "coordination", "dialogue", "socialize", "trust"},
    "work": {"farm", "gather", "haul", "materials", "repair", "shelter", "work"},
    "scarcity": {"distribution", "farm", "food", "haul", "hunger", "scarcity"},
    "identity": {"care", "coordination", "food", "repair", "routes", "trust"},
    "routine": {"farm", "gather", "haul", "repair", "rest", "socialize"},
}

STOP_TERMS = {
    "agent",
    "after",
    "against",
    "and",
    "because",
    "day",
    "from",
    "keep",
    "memory",
    "more",
    "recent",
    "reflection",
    "should",
    "still",
    "that",
    "the",
    "their",
    "through",
    "with",
}


@dataclass(frozen=True)
class ReflectionEvidence:
    day: int
    kind: str
    text: str
    overlap_terms: list[str]


@dataclass(frozen=True)
class BaselinePlanDelta:
    day: int
    run_plan: str
    baseline_plan: str | None
    run_action: str | None
    baseline_action: str | None
    change_kind: str


@dataclass(frozen=True)
class ReflectionFollowThrough:
    day: int
    agent_id: str
    agent_name: str
    status: str
    focus: str
    signal: str
    window_start: int
    window_end: int
    reflection_summary: str
    plan_evidence: list[ReflectionEvidence]
    dialogue_evidence: list[ReflectionEvidence]
    baseline_plan_deltas: list[BaselinePlanDelta]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_reflection_follow_through(
    world: WorldState,
    reflection_trace: list[dict[str, Any]],
    baseline_world: WorldState | None = None,
    window_days: int = 7,
) -> list[ReflectionFollowThrough]:
    """Trace downstream behavior after accepted generated reflections."""
    if window_days < 1:
        raise ValueError("window_days must be >= 1")

    follow_through: list[ReflectionFollowThrough] = []
    for item in reflection_trace:
        if item.get("status") != "primary":
            continue

        agent = _find_agent(world, str(item.get("agent_id", "")))
        summary = str(item.get("used_reflection") or "").strip()
        if agent is None or not summary:
            continue

        reflection_day = int(item["day"])
        window_start = reflection_day + 1
        window_end = min(world.day, reflection_day + window_days)
        focus = str(item.get("focus") or "routine").lower()
        terms = _reflection_terms(summary, focus)
        plan_evidence = _plan_evidence(agent, window_start, window_end, terms)
        dialogue_evidence = _dialogue_evidence(
            world.event_log,
            agent,
            window_start,
            window_end,
            terms,
        )
        baseline_deltas = _baseline_plan_deltas(
            agent,
            _find_agent(baseline_world, agent.id) if baseline_world is not None else None,
            window_start,
            window_end,
        )
        signal = _signal(plan_evidence, dialogue_evidence, baseline_deltas)
        follow_through.append(
            ReflectionFollowThrough(
                day=reflection_day,
                agent_id=agent.id,
                agent_name=agent.name,
                status=str(item.get("status")),
                focus=focus,
                signal=signal,
                window_start=window_start,
                window_end=window_end,
                reflection_summary=summary,
                plan_evidence=plan_evidence,
                dialogue_evidence=dialogue_evidence,
                baseline_plan_deltas=baseline_deltas,
                summary=_summary(
                    agent.name,
                    reflection_day,
                    window_start,
                    window_end,
                    plan_evidence,
                    dialogue_evidence,
                    baseline_deltas,
                    baseline_world is not None,
                ),
            )
        )
    return follow_through


def _find_agent(world: WorldState | None, agent_id: str) -> Agent | None:
    if world is None:
        return None
    return next((agent for agent in world.agents if agent.id == agent_id), None)


def _reflection_terms(summary: str, focus: str) -> set[str]:
    return (_terms(summary) - STOP_TERMS) | FOCUS_TERMS.get(focus, set())


def _plan_evidence(
    agent: Agent,
    window_start: int,
    window_end: int,
    terms: set[str],
) -> list[ReflectionEvidence]:
    evidence = []
    for entry in agent.plan_history:
        day = _entry_day(entry)
        if not window_start <= day <= window_end:
            continue
        overlap = sorted(_terms(entry) & terms)
        if not overlap:
            continue
        evidence.append(
            ReflectionEvidence(
                day=day,
                kind="plan",
                text=entry,
                overlap_terms=overlap,
            )
        )
    return evidence[:6]


def _dialogue_evidence(
    events: list[Event],
    agent: Agent,
    window_start: int,
    window_end: int,
    terms: set[str],
) -> list[ReflectionEvidence]:
    evidence = []
    for event in events:
        if event.kind != "dialogue" or not window_start <= event.day <= window_end:
            continue
        if event.actor_id != agent.id and agent.name not in event.description:
            continue
        overlap = sorted(_terms(event.description) & terms)
        if not overlap:
            continue
        evidence.append(
            ReflectionEvidence(
                day=event.day,
                kind=event.kind,
                text=event.description,
                overlap_terms=overlap,
            )
        )
    return evidence[:4]


def _baseline_plan_deltas(
    agent: Agent,
    baseline_agent: Agent | None,
    window_start: int,
    window_end: int,
) -> list[BaselinePlanDelta]:
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
            BaselinePlanDelta(
                day=day,
                run_plan=run_plan,
                baseline_plan=baseline_plan,
                run_action=_plan_action(run_plan),
                baseline_action=_plan_action(baseline_plan) if baseline_plan is not None else None,
                change_kind=_plan_change_kind(run_plan, baseline_plan),
            )
        )
    return deltas[:7]


def _plans_by_day(agent: Agent, window_start: int, window_end: int) -> dict[int, str]:
    entries = {}
    for entry in agent.plan_history:
        day = _entry_day(entry)
        if window_start <= day <= window_end:
            entries[day] = entry
    return entries


def _signal(
    plan_evidence: list[ReflectionEvidence],
    dialogue_evidence: list[ReflectionEvidence],
    baseline_deltas: list[BaselinePlanDelta],
) -> str:
    if any(item.change_kind == "action" for item in baseline_deltas):
        return "baseline_action_diverged"
    if baseline_deltas:
        return "baseline_plan_context_diverged"
    if plan_evidence and dialogue_evidence:
        return "plan_and_dialogue_echo"
    if plan_evidence:
        return "plan_echo"
    if dialogue_evidence:
        return "dialogue_echo"
    return "no_follow_through"


def _summary(
    agent_name: str,
    reflection_day: int,
    window_start: int,
    window_end: int,
    plan_evidence: list[ReflectionEvidence],
    dialogue_evidence: list[ReflectionEvidence],
    baseline_deltas: list[BaselinePlanDelta],
    has_baseline: bool,
) -> str:
    window = f"days {window_start}-{window_end}"
    action_deltas = sum(1 for item in baseline_deltas if item.change_kind == "action")
    context_deltas = len(baseline_deltas) - action_deltas
    if action_deltas:
        return (
            f"After the generated reflection on day {reflection_day}, {agent_name} "
            f"has {action_deltas} action differences and {context_deltas} "
            f"plan-context differences against the rule baseline "
            f"in {window}; {len(plan_evidence)} later plans and "
            f"{len(dialogue_evidence)} dialogue events overlap reflection terms."
        )
    if context_deltas:
        return (
            f"After the generated reflection on day {reflection_day}, {agent_name} "
            f"keeps the same recorded actions but has {context_deltas} "
            f"plan-context differences against the rule baseline in {window}; "
            f"{len(plan_evidence)} later plans and {len(dialogue_evidence)} "
            "dialogue events overlap reflection terms."
        )
    if plan_evidence or dialogue_evidence:
        suffix = "no rule baseline was supplied"
        if has_baseline:
            suffix = "the rule baseline kept the same recorded plans"
        return (
            f"After the generated reflection on day {reflection_day}, {agent_name} "
            f"has {len(plan_evidence)} later plans and {len(dialogue_evidence)} "
            f"dialogue events overlapping reflection terms in {window}; {suffix}."
        )
    return (
        f"No downstream plan or dialogue evidence was found for {agent_name} in "
        f"{window} after the generated reflection on day {reflection_day}."
    )


def _entry_day(text: str) -> int:
    match = re.search(r"\bday\s+(\d+)\b", text.lower())
    return int(match.group(1)) if match is not None else 0


def _plan_action(text: str) -> str | None:
    match = re.search(r"\bday\s+\d+:\s*([a-z_]+)\s*\|", text.lower())
    return match.group(1) if match is not None else None


def _plan_change_kind(run_plan: str, baseline_plan: str | None) -> str:
    if _plan_action(run_plan) != (_plan_action(baseline_plan) if baseline_plan else None):
        return "action"
    return "context"


def _terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if len(term) > 1
    }
