from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .model import Event, WorldState


INTENT_TERMS = {
    "repair_routes": {"repair", "route", "reopen"},
    "reconcile_relationships": {"socialize", "trust", "relationship", "reconcile"},
    "protect_food": {"farm", "food", "haul", "distribution"},
    "coordinate": {"socialize", "coordinate", "coordination"},
}


@dataclass(frozen=True)
class ObserverIntentFinding:
    day: int
    intent: str
    signal: str
    expected_targets: int
    memory_hits: int
    plan_hits: int
    window_start: int
    window_end: int
    target_agents: list[str]
    plan_evidence: list[str]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_observer_intents(
    world: WorldState,
    horizon_days: int = 7,
) -> list[ObserverIntentFinding]:
    findings = []
    for event in world.event_log:
        intent = _intent_from_event(event)
        if not intent:
            continue
        findings.append(_assess_event(world, event, intent, horizon_days))
    return findings


def _assess_event(
    world: WorldState,
    event: Event,
    intent: str,
    horizon_days: int,
) -> ObserverIntentFinding:
    window_start = event.day
    window_end = event.day + max(0, horizon_days)
    memory_agents = [
        agent
        for agent in world.agents
        if any(
            memory.day == event.day
            and memory.kind == event.kind
            and memory.text == event.description
            for memory in agent.memory_stream
        )
    ]
    terms = INTENT_TERMS.get(intent, {intent})
    plan_evidence = []
    for agent in memory_agents:
        for plan in agent.plan_history:
            day = _plan_day(plan)
            if day is None or day < window_start or day > window_end:
                continue
            if _contains_any(plan, terms):
                plan_evidence.append(f"{agent.name}: {plan}")
                break

    expected_targets = int(event.effects.get("target_count", 0.0))
    memory_hits = len(memory_agents)
    plan_hits = len(plan_evidence)
    signal = _signal(expected_targets, memory_hits, plan_hits)
    return ObserverIntentFinding(
        day=event.day,
        intent=intent,
        signal=signal,
        expected_targets=expected_targets,
        memory_hits=memory_hits,
        plan_hits=plan_hits,
        window_start=window_start,
        window_end=window_end,
        target_agents=[agent.name for agent in memory_agents],
        plan_evidence=plan_evidence[:8],
        summary=_summary(intent, signal, expected_targets, memory_hits, plan_hits),
    )


def _intent_from_event(event: Event) -> str:
    if event.kind != "broadcast":
        return ""
    for key in event.effects:
        if key.startswith("intent_"):
            return key.removeprefix("intent_")
    return ""


def _plan_day(plan: str) -> int | None:
    match = re.match(r"day\s+(\d+):", plan)
    if not match:
        return None
    return int(match.group(1))


def _contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _signal(expected_targets: int, memory_hits: int, plan_hits: int) -> str:
    if expected_targets and memory_hits < expected_targets:
        return "intent_memory_gap"
    if plan_hits:
        return "intent_memory_plan_echo"
    if memory_hits:
        return "intent_memory_only"
    return "intent_not_observed"


def _summary(
    intent: str,
    signal: str,
    expected_targets: int,
    memory_hits: int,
    plan_hits: int,
) -> str:
    return (
        f"Observer intent {intent} produced signal {signal}: "
        f"{memory_hits}/{expected_targets} targets hold the memory and "
        f"{plan_hits} target plans echo the intent."
    )
