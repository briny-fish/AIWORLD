from __future__ import annotations

import re
from dataclasses import asdict
from typing import Iterable

from .model import Agent, Event, MemoryItem


CRITICAL_EVENT_KINDS = {
    "disaster",
    "hunger_crisis",
    "safety_crisis",
    "institutional_crisis",
    "organization_fracture",
    "relationship_crisis",
    "route_blocked",
}

SOCIAL_EVENT_KINDS = {
    "broadcast",
    "dialogue",
    "exchange",
    "market",
    "organization",
    "reconciliation",
    "route_reopened",
    "social",
}


def memory_from_event(event: Event, agent: Agent) -> MemoryItem:
    """Convert an event into the agent-local memory format.

    This is deliberately deterministic. LLMs can later summarize or reinterpret
    these memories, but the durable source material stays replayable.
    """

    tags = _memory_tags(event, agent)
    return MemoryItem(
        day=event.day,
        kind=event.kind,
        text=event.description,
        importance=_memory_importance(event),
        tags=tags,
        actor_id=event.actor_id,
        related_agent_ids=_related_agent_ids(event, agent),
        location_id=agent.location_id,
    )


def retrieve_memories(
    agent: Agent,
    query: str,
    current_day: int,
    limit: int = 8,
) -> list[MemoryItem]:
    """Return memories ranked by importance, recency, and query overlap."""

    if limit < 1:
        return []
    query_terms = _terms(query)
    scored = [
        (_score_memory(memory, query_terms, current_day), index, memory)
        for index, memory in enumerate(agent.memory_stream)
    ]
    scored = [item for item in scored if item[0] > 0.0]
    scored.sort(key=lambda item: (-item[0], -item[2].day, -item[1]))
    return [memory for _, _, memory in scored[:limit]]


def memory_dicts(memories: Iterable[MemoryItem]) -> list[dict]:
    return [asdict(memory) for memory in memories]


def build_reflection(agent: Agent, current_day: int, lookback_days: int) -> str:
    recent = [
        memory
        for memory in agent.memory_stream
        if current_day - lookback_days < memory.day <= current_day
    ]
    if not recent:
        return f"{agent.name} has little new evidence and keeps their current priorities."

    critical = [memory for memory in recent if memory.kind in CRITICAL_EVENT_KINDS]
    social = [memory for memory in recent if memory.kind in SOCIAL_EVENT_KINDS]
    work = [memory for memory in recent if memory.kind in {"work", "transport", "maintenance"}]
    top = max(recent, key=lambda memory: (memory.importance, memory.day))

    parts: list[str] = []
    if critical:
        parts.append(f"{len(critical)} crises or shocks require caution")
    if social:
        parts.append(f"{len(social)} social or institutional moments shaped trust")
    if work:
        parts.append(f"{len(work)} work memories show where effort has been spent")
    if not parts:
        parts.append("recent life was mostly routine")
    top_text = top.text.rstrip(".")
    parts.append(f"most salient memory: {top_text}")
    return f"{agent.name} reflects that " + "; ".join(parts) + "."


def _score_memory(memory: MemoryItem, query_terms: set[str], current_day: int) -> float:
    age = max(0, current_day - memory.day)
    recency = 1.0 / (1.0 + age / 14.0)
    text_terms = _terms(" ".join([memory.text, memory.kind, " ".join(memory.tags)]))
    overlap = len(query_terms & text_terms) / max(len(query_terms), 1)
    social_bonus = 0.10 if memory.kind in SOCIAL_EVENT_KINDS else 0.0
    crisis_bonus = 0.16 if memory.kind in CRITICAL_EVENT_KINDS else 0.0
    return memory.importance * 1.25 + recency * 0.45 + overlap * 0.60 + social_bonus + crisis_bonus


def _memory_importance(event: Event) -> float:
    if event.kind in CRITICAL_EVENT_KINDS:
        return 0.95
    if event.kind in {"reflection", "edict", "intervention"}:
        return 0.76
    if event.kind in SOCIAL_EVENT_KINDS:
        return 0.62
    if event.kind in {"plan_blocked", "rationing", "route_strain"}:
        return 0.58
    if event.kind in {"work", "transport", "cooperation", "maintenance"}:
        return 0.42
    if event.kind == "rest":
        return 0.30
    return 0.36


def _memory_tags(event: Event, agent: Agent) -> list[str]:
    tags = {event.kind, event.actor_id, agent.location_id, agent.role}
    tags.update(event.effects.keys())
    tags.update(agent.organization_ids)
    for term in _terms(event.description):
        if term in {
            "food",
            "materials",
            "shelter",
            "trust",
            "storm",
            "disaster",
            "rationing",
            "repair",
            "route",
            "exchange",
            "social",
            "fracture",
            "reconciliation",
        }:
            tags.add(term)
    return sorted(tag for tag in tags if tag)


def _related_agent_ids(event: Event, agent: Agent) -> list[str]:
    related = {event.actor_id}
    for other_id in agent.relationships:
        if other_id in event.description:
            related.add(other_id)
    related.discard(agent.id)
    return sorted(related)


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(term) > 1}
