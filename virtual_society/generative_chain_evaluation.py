from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .model import Agent, MemoryItem, WorldState


FOCUS_TERMS = {
    "care": {"care", "clinic", "support", "vulnerable"},
    "coordination": {"council", "coordination", "routes", "trust", "warning"},
    "identity": {"care", "coordination", "food", "repair", "routes", "trust"},
    "relationship": {"belonging", "relationship", "social", "ties", "trust"},
    "routine": {"farm", "gather", "haul", "repair", "rest", "socialize"},
    "scarcity": {"distribution", "farm", "food", "hunger", "scarcity"},
    "shock": {"damage", "damaged", "disaster", "repair", "shock", "storm"},
    "social": {"care", "coordination", "dialogue", "socialize", "trust"},
    "work": {"farm", "gather", "haul", "materials", "repair", "shelter", "work"},
}

STOP_TERMS = {
    "about",
    "after",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "because",
    "day",
    "dialogue",
    "for",
    "from",
    "generated",
    "has",
    "have",
    "her",
    "his",
    "in",
    "is",
    "it",
    "its",
    "into",
    "not",
    "of",
    "on",
    "or",
    "recent",
    "reflection",
    "so",
    "that",
    "the",
    "their",
    "they",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
}


@dataclass(frozen=True)
class ChainEvidence:
    day: int
    agent_id: str
    agent_name: str
    kind: str
    text: str
    overlap_terms: list[str]


@dataclass(frozen=True)
class ChainPlanDelta:
    day: int
    run_plan: str
    baseline_plan: str | None
    run_action: str | None
    baseline_action: str | None
    change_kind: str


@dataclass(frozen=True)
class GeneratedChain:
    dialogue_day: int
    reflection_day: int
    speaker_id: str
    speaker_name: str
    partner_id: str
    partner_name: str
    reflection_agent_id: str
    reflection_agent_name: str
    dialogue_focus: str
    reflection_focus: str
    signal: str
    shared_terms: list[str]
    generated_dialogue: str
    generated_reflection: str
    memory_evidence: list[ChainEvidence]
    plan_evidence: list[ChainEvidence]
    baseline_plan_deltas: list[ChainPlanDelta]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_generated_chains(
    world: WorldState,
    dialogue_trace: list[dict[str, Any]],
    reflection_trace: list[dict[str, Any]],
    baseline_world: WorldState | None = None,
    reflection_window_days: int = 7,
    plan_window_days: int = 7,
) -> list[GeneratedChain]:
    """Match generated dialogues to generated reflections and later plans."""
    if reflection_window_days < 0:
        raise ValueError("reflection_window_days must be >= 0")
    if plan_window_days < 1:
        raise ValueError("plan_window_days must be >= 1")

    chains: list[GeneratedChain] = []
    accepted_reflections = [
        item
        for item in reflection_trace
        if item.get("status") == "primary" and str(item.get("used_reflection") or "").strip()
    ]

    for dialogue in dialogue_trace:
        if dialogue.get("status") != "primary":
            continue

        speaker = _find_agent(world, str(dialogue.get("speaker_id", "")))
        partner = _find_agent(world, str(dialogue.get("partner_id", "")))
        generated_dialogue = str(dialogue.get("used_dialogue") or "").strip()
        if speaker is None or partner is None or not generated_dialogue:
            continue

        dialogue_day = int(dialogue["day"])
        participants = {speaker.id: speaker, partner.id: partner}
        dialogue_focus = str(dialogue.get("focus") or "routine").lower()
        dialogue_terms = _content_terms(generated_dialogue)
        dialogue_context_terms = _context_terms(generated_dialogue, dialogue_focus)

        for reflection in accepted_reflections:
            reflection_agent_id = str(reflection.get("agent_id", ""))
            if reflection_agent_id not in participants:
                continue
            reflection_day = int(reflection["day"])
            if not dialogue_day <= reflection_day <= dialogue_day + reflection_window_days:
                continue

            reflection_agent = participants[reflection_agent_id]
            generated_reflection = str(reflection.get("used_reflection") or "").strip()
            reflection_focus = str(reflection.get("focus") or "routine").lower()
            reflection_terms = _content_terms(generated_reflection)
            reflection_context_terms = _context_terms(generated_reflection, reflection_focus)
            name_terms = _terms(" ".join([speaker.name, partner.name, reflection_agent.name]))
            shared_terms = sorted((dialogue_terms & reflection_terms) - name_terms)
            evidence_terms = set(shared_terms) or (
                dialogue_context_terms & reflection_context_terms
            )
            if not evidence_terms:
                evidence_terms = reflection_terms | dialogue_terms

            plan_window_start = reflection_day + 1
            plan_window_end = min(world.day, reflection_day + plan_window_days)
            memory_evidence = _memory_evidence(
                reflection_agent,
                dialogue_day,
                generated_dialogue,
                evidence_terms,
            )
            plan_evidence = _plan_evidence(
                reflection_agent,
                plan_window_start,
                plan_window_end,
                evidence_terms,
            )
            baseline_deltas = _baseline_plan_deltas(
                reflection_agent,
                _find_agent(baseline_world, reflection_agent.id)
                if baseline_world is not None
                else None,
                plan_window_start,
                plan_window_end,
            )
            signal = _signal(shared_terms, memory_evidence, plan_evidence, baseline_deltas)
            chains.append(
                GeneratedChain(
                    dialogue_day=dialogue_day,
                    reflection_day=reflection_day,
                    speaker_id=speaker.id,
                    speaker_name=speaker.name,
                    partner_id=partner.id,
                    partner_name=partner.name,
                    reflection_agent_id=reflection_agent.id,
                    reflection_agent_name=reflection_agent.name,
                    dialogue_focus=dialogue_focus,
                    reflection_focus=reflection_focus,
                    signal=signal,
                    shared_terms=shared_terms[:12],
                    generated_dialogue=generated_dialogue,
                    generated_reflection=generated_reflection,
                    memory_evidence=memory_evidence,
                    plan_evidence=plan_evidence,
                    baseline_plan_deltas=baseline_deltas,
                    summary=_summary(
                        dialogue_day,
                        reflection_day,
                        speaker.name,
                        partner.name,
                        reflection_agent.name,
                        shared_terms,
                        memory_evidence,
                        plan_evidence,
                        baseline_deltas,
                        baseline_world is not None,
                    ),
                )
            )
    return chains


def _find_agent(world: WorldState | None, agent_id: str) -> Agent | None:
    if world is None:
        return None
    return next((agent for agent in world.agents if agent.id == agent_id), None)


def _content_terms(text: str) -> set[str]:
    return _terms(text) - STOP_TERMS


def _context_terms(text: str, focus: str) -> set[str]:
    return _content_terms(text) | FOCUS_TERMS.get(focus, set())


def _memory_evidence(
    agent: Agent,
    dialogue_day: int,
    generated_dialogue: str,
    terms: set[str],
) -> list[ChainEvidence]:
    for memory in agent.memory_stream:
        if memory.day != dialogue_day or memory.kind != "dialogue":
            continue
        overlap = sorted(_terms(memory.text) & terms)
        if memory.text != generated_dialogue and not overlap:
            continue
        return [_evidence_from_memory(agent, memory, overlap)]
    return []


def _evidence_from_memory(
    agent: Agent,
    memory: MemoryItem,
    overlap_terms: list[str],
) -> ChainEvidence:
    return ChainEvidence(
        day=memory.day,
        agent_id=agent.id,
        agent_name=agent.name,
        kind=memory.kind,
        text=memory.text,
        overlap_terms=overlap_terms,
    )


def _plan_evidence(
    agent: Agent,
    window_start: int,
    window_end: int,
    terms: set[str],
) -> list[ChainEvidence]:
    evidence = []
    for entry in agent.plan_history:
        day = _entry_day(entry)
        if not window_start <= day <= window_end:
            continue
        overlap = sorted(_terms(entry) & terms)
        if not overlap:
            continue
        evidence.append(
            ChainEvidence(
                day=day,
                agent_id=agent.id,
                agent_name=agent.name,
                kind="plan",
                text=entry,
                overlap_terms=overlap,
            )
        )
    return evidence[:6]


def _baseline_plan_deltas(
    agent: Agent,
    baseline_agent: Agent | None,
    window_start: int,
    window_end: int,
) -> list[ChainPlanDelta]:
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
            ChainPlanDelta(
                day=day,
                run_plan=run_plan,
                baseline_plan=baseline_plan,
                run_action=_plan_action(run_plan),
                baseline_action=_plan_action(baseline_plan),
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
    shared_terms: list[str],
    memory_evidence: list[ChainEvidence],
    plan_evidence: list[ChainEvidence],
    baseline_deltas: list[ChainPlanDelta],
) -> str:
    if any(item.change_kind == "action" for item in baseline_deltas):
        return "generated_chain_action_diverged"
    if baseline_deltas:
        return "generated_chain_plan_context_diverged"
    if shared_terms and memory_evidence and plan_evidence:
        return "generated_chain_plan_echo"
    if shared_terms and memory_evidence:
        return "generated_chain_reflection_echo"
    return "weak_generated_chain"


def _summary(
    dialogue_day: int,
    reflection_day: int,
    speaker_name: str,
    partner_name: str,
    reflection_agent_name: str,
    shared_terms: list[str],
    memory_evidence: list[ChainEvidence],
    plan_evidence: list[ChainEvidence],
    baseline_deltas: list[ChainPlanDelta],
    has_baseline: bool,
) -> str:
    action_deltas = sum(1 for item in baseline_deltas if item.change_kind == "action")
    context_deltas = len(baseline_deltas) - action_deltas
    term_text = ", ".join(shared_terms[:6]) or "none"
    baseline_text = "no rule baseline was supplied"
    if has_baseline and not baseline_deltas:
        baseline_text = "no baseline plan deltas were found"
    elif action_deltas or context_deltas:
        baseline_text = (
            f"{action_deltas} action deltas and {context_deltas} plan-context deltas"
        )
    return (
        f"Generated dialogue on day {dialogue_day} between {speaker_name} and "
        f"{partner_name} links to {reflection_agent_name}'s generated reflection "
        f"on day {reflection_day}; shared terms: {term_text}; "
        f"memory hits {len(memory_evidence)}, plan echoes {len(plan_evidence)}, "
        f"{baseline_text}."
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
