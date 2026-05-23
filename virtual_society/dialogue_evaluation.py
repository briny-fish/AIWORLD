from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .model import Agent, MemoryItem, WorldState


FOCUS_TERMS = {
    "shock": {"damage", "damaged", "disaster", "repair", "shock", "storm"},
    "care": {"care", "clinic", "suffering", "support", "vulnerable"},
    "coordination": {"council", "coordination", "routes", "trust", "warning"},
    "scarcity": {"distribution", "farm", "food", "hunger", "scarcity"},
    "relationship": {"belonging", "relationship", "social", "ties", "trust"},
    "routine": {"farm", "gather", "haul", "repair", "rest", "socialize"},
}

STOP_TERMS = {
    "about",
    "after",
    "and",
    "because",
    "day",
    "dialogue",
    "discussed",
    "from",
    "into",
    "recent",
    "that",
    "the",
    "their",
    "they",
    "this",
    "with",
}


@dataclass(frozen=True)
class DialogueFollowEvidence:
    day: int
    agent_id: str
    agent_name: str
    kind: str
    text: str
    overlap_terms: list[str]


@dataclass(frozen=True)
class BaselineTextDelta:
    day: int
    agent_id: str
    agent_name: str
    run_text: str
    baseline_text: str | None
    change_kind: str


@dataclass(frozen=True)
class DialogueFollowThrough:
    day: int
    speaker_id: str
    speaker_name: str
    partner_id: str
    partner_name: str
    status: str
    focus: str
    signal: str
    window_start: int
    window_end: int
    generated_dialogue: str
    baseline_dialogue: str
    memory_evidence: list[DialogueFollowEvidence]
    reflection_evidence: list[DialogueFollowEvidence]
    plan_evidence: list[DialogueFollowEvidence]
    baseline_reflection_deltas: list[BaselineTextDelta]
    baseline_plan_deltas: list[BaselineTextDelta]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_dialogue_follow_through(
    world: WorldState,
    dialogue_trace: list[dict[str, Any]],
    baseline_world: WorldState | None = None,
    window_days: int = 14,
) -> list[DialogueFollowThrough]:
    """Trace whether accepted generated dialogue enters later social cognition."""
    if window_days < 1:
        raise ValueError("window_days must be >= 1")

    follow_through: list[DialogueFollowThrough] = []
    for item in dialogue_trace:
        if item.get("status") != "primary":
            continue

        speaker = _find_agent(world, str(item.get("speaker_id", "")))
        partner = _find_agent(world, str(item.get("partner_id", "")))
        generated_dialogue = str(item.get("used_dialogue") or "").strip()
        baseline_dialogue = str(item.get("baseline_dialogue") or "").strip()
        if speaker is None or partner is None or not generated_dialogue:
            continue

        dialogue_day = int(item["day"])
        window_start = dialogue_day + 1
        window_end = min(world.day, dialogue_day + window_days)
        participants = [speaker, partner]
        focus = str(item.get("focus") or "routine").lower()
        terms = _dialogue_terms(generated_dialogue, focus)
        memory_evidence = _memory_evidence(
            participants,
            dialogue_day,
            generated_dialogue,
            terms,
        )
        reflection_evidence = _reflection_evidence(
            participants,
            window_start,
            window_end,
            terms,
        )
        plan_evidence = _plan_evidence(
            participants,
            window_start,
            window_end,
            terms,
        )
        baseline_participants = [
            _find_agent(baseline_world, speaker.id),
            _find_agent(baseline_world, partner.id),
        ]
        baseline_reflection_deltas = _baseline_text_deltas(
            participants,
            baseline_participants,
            window_start,
            window_end,
            field="reflection",
        )
        baseline_plan_deltas = _baseline_text_deltas(
            participants,
            baseline_participants,
            window_start,
            window_end,
            field="plan",
        )
        signal = _signal(
            memory_evidence,
            reflection_evidence,
            plan_evidence,
            baseline_reflection_deltas,
            baseline_plan_deltas,
        )
        follow_through.append(
            DialogueFollowThrough(
                day=dialogue_day,
                speaker_id=speaker.id,
                speaker_name=speaker.name,
                partner_id=partner.id,
                partner_name=partner.name,
                status=str(item.get("status")),
                focus=focus,
                signal=signal,
                window_start=window_start,
                window_end=window_end,
                generated_dialogue=generated_dialogue,
                baseline_dialogue=baseline_dialogue,
                memory_evidence=memory_evidence,
                reflection_evidence=reflection_evidence,
                plan_evidence=plan_evidence,
                baseline_reflection_deltas=baseline_reflection_deltas,
                baseline_plan_deltas=baseline_plan_deltas,
                summary=_summary(
                    speaker.name,
                    partner.name,
                    dialogue_day,
                    window_start,
                    window_end,
                    memory_evidence,
                    reflection_evidence,
                    plan_evidence,
                    baseline_reflection_deltas,
                    baseline_plan_deltas,
                    baseline_world is not None,
                ),
            )
        )
    return follow_through


def _find_agent(world: WorldState | None, agent_id: str) -> Agent | None:
    if world is None:
        return None
    return next((agent for agent in world.agents if agent.id == agent_id), None)


def _dialogue_terms(text: str, focus: str) -> set[str]:
    return (_terms(text) - STOP_TERMS) | FOCUS_TERMS.get(focus, set())


def _memory_evidence(
    agents: list[Agent],
    dialogue_day: int,
    generated_dialogue: str,
    terms: set[str],
) -> list[DialogueFollowEvidence]:
    evidence = []
    for agent in agents:
        for memory in agent.memory_stream:
            if memory.day != dialogue_day or memory.kind != "dialogue":
                continue
            if memory.text != generated_dialogue and not (_terms(memory.text) & terms):
                continue
            evidence.append(
                _evidence_from_memory(agent, memory, sorted(_terms(memory.text) & terms))
            )
            break
    return evidence


def _evidence_from_memory(
    agent: Agent,
    memory: MemoryItem,
    overlap_terms: list[str],
) -> DialogueFollowEvidence:
    return DialogueFollowEvidence(
        day=memory.day,
        agent_id=agent.id,
        agent_name=agent.name,
        kind=memory.kind,
        text=memory.text,
        overlap_terms=overlap_terms,
    )


def _reflection_evidence(
    agents: list[Agent],
    window_start: int,
    window_end: int,
    terms: set[str],
) -> list[DialogueFollowEvidence]:
    evidence = []
    for agent in agents:
        for entry in agent.reflections:
            day = _entry_day(entry)
            if not window_start <= day <= window_end:
                continue
            overlap = sorted(_terms(entry) & terms)
            if not overlap:
                continue
            evidence.append(_entry_evidence(agent, day, "reflection", entry, overlap))
    return evidence[:6]


def _plan_evidence(
    agents: list[Agent],
    window_start: int,
    window_end: int,
    terms: set[str],
) -> list[DialogueFollowEvidence]:
    evidence = []
    for agent in agents:
        for entry in agent.plan_history:
            day = _entry_day(entry)
            if not window_start <= day <= window_end:
                continue
            overlap = sorted(_terms(entry) & terms)
            if not overlap:
                continue
            evidence.append(_entry_evidence(agent, day, "plan", entry, overlap))
    return evidence[:8]


def _entry_evidence(
    agent: Agent,
    day: int,
    kind: str,
    text: str,
    overlap_terms: list[str],
) -> DialogueFollowEvidence:
    return DialogueFollowEvidence(
        day=day,
        agent_id=agent.id,
        agent_name=agent.name,
        kind=kind,
        text=text,
        overlap_terms=overlap_terms,
    )


def _baseline_text_deltas(
    agents: list[Agent],
    baseline_agents: list[Agent | None],
    window_start: int,
    window_end: int,
    field: str,
) -> list[BaselineTextDelta]:
    deltas = []
    for agent, baseline_agent in zip(agents, baseline_agents):
        if baseline_agent is None:
            continue
        run_entries = _entries_by_day(agent, window_start, window_end, field)
        baseline_entries = _entries_by_day(baseline_agent, window_start, window_end, field)
        for day in sorted(set(run_entries) | set(baseline_entries)):
            run_text = run_entries.get(day)
            baseline_text = baseline_entries.get(day)
            if run_text is None or run_text == baseline_text:
                continue
            deltas.append(
                BaselineTextDelta(
                    day=day,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    run_text=run_text,
                    baseline_text=baseline_text,
                    change_kind=(
                        _plan_change_kind(run_text, baseline_text)
                        if field == "plan"
                        else "context"
                    ),
                )
            )
    return deltas[:8]


def _entries_by_day(
    agent: Agent,
    window_start: int,
    window_end: int,
    field: str,
) -> dict[int, str]:
    source = agent.plan_history if field == "plan" else agent.reflections
    entries = {}
    for entry in source:
        day = _entry_day(entry)
        if window_start <= day <= window_end:
            entries[day] = entry
    return entries


def _signal(
    memory_evidence: list[DialogueFollowEvidence],
    reflection_evidence: list[DialogueFollowEvidence],
    plan_evidence: list[DialogueFollowEvidence],
    baseline_reflection_deltas: list[BaselineTextDelta],
    baseline_plan_deltas: list[BaselineTextDelta],
) -> str:
    if any(item.change_kind == "action" for item in baseline_plan_deltas):
        return "baseline_action_diverged"
    if baseline_reflection_deltas:
        return "baseline_reflection_context_diverged"
    if baseline_plan_deltas:
        return "baseline_plan_context_diverged"
    if memory_evidence and reflection_evidence and plan_evidence:
        return "memory_reflection_plan_echo"
    if memory_evidence and reflection_evidence:
        return "memory_reflection_echo"
    if memory_evidence and plan_evidence:
        return "memory_plan_echo"
    if memory_evidence:
        return "memory_only"
    return "no_follow_through"


def _summary(
    speaker_name: str,
    partner_name: str,
    dialogue_day: int,
    window_start: int,
    window_end: int,
    memory_evidence: list[DialogueFollowEvidence],
    reflection_evidence: list[DialogueFollowEvidence],
    plan_evidence: list[DialogueFollowEvidence],
    baseline_reflection_deltas: list[BaselineTextDelta],
    baseline_plan_deltas: list[BaselineTextDelta],
    has_baseline: bool,
) -> str:
    window = f"days {window_start}-{window_end}"
    action_deltas = sum(1 for item in baseline_plan_deltas if item.change_kind == "action")
    plan_context_deltas = len(baseline_plan_deltas) - action_deltas
    if action_deltas:
        return (
            f"After generated dialogue on day {dialogue_day}, {speaker_name} and "
            f"{partner_name} show {len(memory_evidence)} memory hits, "
            f"{len(reflection_evidence)} reflection echoes, {len(plan_evidence)} plan echoes, "
            f"and {action_deltas} action differences against the rule baseline in {window}."
        )
    if baseline_reflection_deltas or plan_context_deltas:
        return (
            f"After generated dialogue on day {dialogue_day}, {speaker_name} and "
            f"{partner_name} show {len(memory_evidence)} memory hits, "
            f"{len(reflection_evidence)} reflection echoes, {len(plan_evidence)} plan echoes, "
            f"{len(baseline_reflection_deltas)} reflection-context differences, and "
            f"{plan_context_deltas} plan-context differences against the rule baseline in {window}."
        )
    suffix = "no rule baseline was supplied"
    if has_baseline:
        suffix = "no baseline text deltas were found"
    return (
        f"After generated dialogue on day {dialogue_day}, {speaker_name} and "
        f"{partner_name} show {len(memory_evidence)} memory hits, "
        f"{len(reflection_evidence)} reflection echoes, and {len(plan_evidence)} "
        f"plan echoes in {window}; {suffix}."
    )


def _entry_day(text: str) -> int:
    match = re.search(r"\bday\s+(\d+)\b", text.lower())
    return int(match.group(1)) if match is not None else 0


def _plan_action(text: str | None) -> str | None:
    if text is None:
        return None
    match = re.search(r"\bday\s+\d+:\s*([a-z_]+)\s*\|", text.lower())
    return match.group(1) if match is not None else None


def _plan_change_kind(run_plan: str, baseline_plan: str | None) -> str:
    if _plan_action(run_plan) != _plan_action(baseline_plan):
        return "action"
    return "context"


def _terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if len(term) > 1
    }
