from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .generative_memory import CRITICAL_EVENT_KINDS
from .model import Agent, MemoryItem, WorldState


class DialogueParseError(ValueError):
    pass


@dataclass(frozen=True)
class DialogueProposal:
    text: str
    focus: str = "routine"
    memory_refs: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DialogueContext:
    speaker: dict[str, Any]
    partner: dict[str, Any]
    relationship: dict[str, Any]
    world: dict[str, Any]
    baseline_dialogue: str
    recent_memories: list[dict[str, Any]]
    allowed_focus: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_dialogue_context(
    speaker: Agent,
    partner: Agent,
    world: WorldState,
    baseline_dialogue: str,
    memory_limit: int = 12,
) -> DialogueContext:
    memories = _dialogue_memories(speaker, partner, world.day, memory_limit)
    trust = (
        speaker.relationships.get(partner.id, 0.50)
        + partner.relationships.get(speaker.id, 0.50)
    ) / 2
    return DialogueContext(
        speaker=_agent_context(speaker),
        partner=_agent_context(partner),
        relationship={
            "average_trust": round(trust, 3),
            "shared_organization_ids": sorted(
                set(speaker.organization_ids) & set(partner.organization_ids)
            ),
        },
        world={
            "day": world.day,
            "resources": dict(world.resources),
            "recent_events": [asdict(event) for event in world.event_log[-12:]],
        },
        baseline_dialogue=baseline_dialogue,
        recent_memories=[
            {
                "ref": index,
                "owner_id": owner_id,
                "owner_name": owner_name,
                "day": memory.day,
                "kind": memory.kind,
                "text": memory.text,
                "importance": memory.importance,
                "tags": list(memory.tags),
            }
            for index, (owner_id, owner_name, memory) in enumerate(memories)
        ],
        allowed_focus=[
            "shock",
            "care",
            "coordination",
            "scarcity",
            "relationship",
            "routine",
        ],
    )


def render_dialogue_prompt(context: DialogueContext) -> str:
    payload = json.dumps(context.as_dict(), ensure_ascii=False, indent=2)
    return (
        "You are a dialogue module for a deterministic virtual society.\n"
        "Return exactly one JSON object with keys: text, focus, memory_refs.\n"
        "text is one concise event description of what these two agents said "
        "to each other. It may carry perspective, tension, or coordination, "
        "but it must not invent world facts or mutate world state.\n"
        "memory_refs must be a JSON array of refs from recent_memories that "
        "support the dialogue. When recent_memories is non-empty, use at least "
        "one ref. focus must be one of allowed_focus.\n"
        "baseline_dialogue is the deterministic fallback. You may improve its "
        "specificity using profiles, trust, organizations, memories, and recent "
        "events while keeping the dialogue grounded.\n\n"
        f"Context:\n{payload}"
    )


def parse_dialogue_response(data: dict[str, Any], memory_count: int) -> DialogueProposal:
    if not isinstance(data, dict):
        raise DialogueParseError("Dialogue response must be a JSON object")

    text = str(data.get("text", "")).strip()
    if not text:
        raise DialogueParseError("Dialogue text is required")
    if len(text) > 1000:
        raise DialogueParseError("Dialogue text must be <= 1000 characters")

    focus = str(data.get("focus", "routine")).strip().lower()
    allowed_focus = {
        "shock",
        "care",
        "coordination",
        "scarcity",
        "relationship",
        "routine",
    }
    if focus not in allowed_focus:
        raise DialogueParseError("Dialogue focus is invalid")

    raw_refs = data.get("memory_refs", [])
    if not isinstance(raw_refs, list):
        raise DialogueParseError("Dialogue memory_refs must be a list")
    memory_refs: list[int] = []
    for value in raw_refs:
        try:
            ref = int(value)
        except (TypeError, ValueError) as exc:
            raise DialogueParseError("Dialogue memory_refs must be integers") from exc
        if ref < 0 or ref >= memory_count:
            raise DialogueParseError("Dialogue memory_refs must cite recent memories")
        if ref not in memory_refs:
            memory_refs.append(ref)

    if memory_count > 0 and not memory_refs:
        raise DialogueParseError("Dialogue must cite recent memories")

    return DialogueProposal(text=text, focus=focus, memory_refs=memory_refs)


def _agent_context(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "profile": asdict(agent.profile),
        "organization_ids": list(agent.organization_ids),
        "recent_reflections": agent.reflections[-3:],
    }


def _dialogue_memories(
    speaker: Agent,
    partner: Agent,
    current_day: int,
    memory_limit: int,
) -> list[tuple[str, str, MemoryItem]]:
    memories = [
        (speaker.id, speaker.name, memory)
        for memory in speaker.memory_stream[-16:]
        if current_day - memory.day <= 21
    ]
    memories.extend(
        (partner.id, partner.name, memory)
        for memory in partner.memory_stream[-16:]
        if current_day - memory.day <= 21
    )
    memories.sort(
        key=lambda item: (
            item[2].kind in CRITICAL_EVENT_KINDS,
            item[2].importance,
            item[2].day,
        ),
        reverse=True,
    )
    return memories[:memory_limit]
