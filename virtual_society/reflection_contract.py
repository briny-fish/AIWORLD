from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .generative_memory import CRITICAL_EVENT_KINDS
from .model import Agent, MemoryItem, WorldState


class ReflectionParseError(ValueError):
    pass


@dataclass(frozen=True)
class ReflectionProposal:
    summary: str
    focus: str = "routine"
    memory_refs: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReflectionContext:
    agent: dict[str, Any]
    world: dict[str, Any]
    baseline_reflection: str
    recent_memories: list[dict[str, Any]]
    allowed_focus: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_reflection_context(
    agent: Agent,
    world: WorldState,
    current_day: int,
    lookback_days: int,
    baseline_reflection: str,
    memory_limit: int = 12,
) -> ReflectionContext:
    recent = _reflection_memories(agent, current_day, lookback_days, memory_limit)
    return ReflectionContext(
        agent={
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "profile": asdict(agent.profile),
            "needs": asdict(agent.needs),
            "organization_ids": list(agent.organization_ids),
            "recent_plan_history": agent.plan_history[-6:],
            "recent_reflections": agent.reflections[-3:],
        },
        world={
            "day": world.day,
            "population": world.population,
            "resources": dict(world.resources),
            "recent_events": [
                asdict(event)
                for event in world.event_log
                if current_day - lookback_days < event.day <= current_day
            ][-16:],
        },
        baseline_reflection=baseline_reflection,
        recent_memories=[
            {
                "ref": index,
                "day": memory.day,
                "kind": memory.kind,
                "text": memory.text,
                "importance": memory.importance,
                "tags": list(memory.tags),
            }
            for index, memory in enumerate(recent)
        ],
        allowed_focus=["shock", "social", "work", "scarcity", "identity", "routine"],
    )


def render_reflection_prompt(context: ReflectionContext) -> str:
    payload = json.dumps(context.as_dict(), ensure_ascii=False, indent=2)
    return (
        "You are a reflection module for a deterministic virtual society.\n"
        "Return exactly one JSON object with keys: summary, focus, memory_refs.\n"
        "The summary is a concise reflection for this agent after the recent "
        "lookback window. Use identity, values, goals, plans, and recent "
        "memories, but do not invent world facts.\n"
        "memory_refs must be a JSON array of refs from recent_memories that "
        "support the summary. When recent_memories is non-empty, use at least "
        "one ref. focus must be one of allowed_focus.\n"
        "baseline_reflection is the deterministic fallback. You may improve it "
        "with a more agent-specific interpretation, but keep the reflection "
        "grounded in the provided evidence.\n\n"
        f"Context:\n{payload}"
    )


def parse_reflection_response(
    data: dict[str, Any],
    memory_count: int,
) -> ReflectionProposal:
    if not isinstance(data, dict):
        raise ReflectionParseError("Reflection response must be a JSON object")

    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise ReflectionParseError("Reflection summary is required")
    if len(summary) > 700:
        raise ReflectionParseError("Reflection summary must be <= 700 characters")

    focus = str(data.get("focus", "experience")).strip().lower()
    allowed_focus = {"shock", "social", "work", "scarcity", "identity", "routine"}
    if focus not in allowed_focus:
        raise ReflectionParseError("Reflection focus is invalid")

    raw_refs = data.get("memory_refs", [])
    if not isinstance(raw_refs, list):
        raise ReflectionParseError("Reflection memory_refs must be a list")
    memory_refs: list[int] = []
    for value in raw_refs:
        try:
            ref = int(value)
        except (TypeError, ValueError) as exc:
            raise ReflectionParseError("Reflection memory_refs must be integers") from exc
        if ref < 0 or ref >= memory_count:
            raise ReflectionParseError("Reflection memory_refs must cite recent memories")
        if ref not in memory_refs:
            memory_refs.append(ref)

    if memory_count > 0 and not memory_refs:
        raise ReflectionParseError("Reflection must cite recent memories")

    return ReflectionProposal(summary=summary, focus=focus, memory_refs=memory_refs)


def _reflection_memories(
    agent: Agent,
    current_day: int,
    lookback_days: int,
    memory_limit: int,
) -> list[MemoryItem]:
    recent = [
        memory
        for memory in agent.memory_stream
        if current_day - lookback_days < memory.day <= current_day
    ]
    recent.sort(
        key=lambda memory: (
            memory.kind in CRITICAL_EVENT_KINDS,
            memory.importance,
            memory.day,
        ),
        reverse=True,
    )
    return recent[:memory_limit]
