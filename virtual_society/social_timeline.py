from __future__ import annotations

import re
from typing import Any

from .model import Agent, Event, MemoryItem, WorldState


SOCIAL_TIMELINE_VERSION = "social-timeline-v1"


SOCIAL_EVENT_KINDS = {
    "broadcast",
    "dialogue",
    "exchange",
    "institutional_crisis",
    "market",
    "mediation",
    "organization",
    "organization_fracture",
    "reconciliation",
    "reflection",
    "relationship_crisis",
    "route_blocked",
    "route_reopened",
    "social",
}


CHAIN_SOURCE_KINDS = {
    "broadcast",
    "dialogue",
    "mediation",
    "organization_fracture",
    "reconciliation",
    "relationship_crisis",
}


STOP_TERMS = {
    "about",
    "after",
    "and",
    "are",
    "before",
    "day",
    "for",
    "from",
    "has",
    "have",
    "into",
    "next",
    "not",
    "the",
    "their",
    "then",
    "this",
    "to",
    "was",
    "were",
    "with",
}


def build_social_feed(
    world: WorldState,
    *,
    dialogue_trace: list[dict[str, Any]] | None = None,
    generated_chains: list[dict[str, Any]] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    entries = _social_entries(
        world,
        dialogue_trace=dialogue_trace or [],
        generated_chains=generated_chains or [],
    )
    if limit >= 0:
        entries = entries[-limit:]
    return {
        "kind": "social_feed",
        "version": SOCIAL_TIMELINE_VERSION,
        "day": world.day,
        "entries": entries,
    }


def build_agent_social_history(
    world: WorldState,
    agent_id: str,
    *,
    dialogue_trace: list[dict[str, Any]] | None = None,
    generated_chains: list[dict[str, Any]] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    agent = _find_agent(world, agent_id)
    if agent is None:
        raise ValueError(f"unknown agent id: {agent_id}")

    entries = [
        entry
        for entry in _social_entries(
            world,
            dialogue_trace=dialogue_trace or [],
            generated_chains=generated_chains or [],
        )
        if _entry_involves_agent(entry, agent_id)
    ]
    if limit >= 0:
        entries = entries[-limit:]
    chains = build_influence_chains(
        world,
        generated_chains=generated_chains or [],
        agent_id=agent_id,
        limit=max(1, min(10, limit)),
    )["chains"]
    return {
        "kind": "agent_social_history",
        "version": SOCIAL_TIMELINE_VERSION,
        "day": world.day,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "entries": entries,
        "influence_chains": chains,
    }


def build_influence_chains(
    world: WorldState,
    *,
    generated_chains: list[dict[str, Any]] | None = None,
    agent_id: str | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    chains: list[dict[str, Any]] = []
    for item in generated_chains or []:
        converted = _chain_from_generated_chain(item)
        if converted and (agent_id is None or _chain_involves_agent(converted, agent_id)):
            chains.append(converted)

    generated_source_ids = {chain["source_event_id"] for chain in chains}
    for entry in _social_entries(world, dialogue_trace=[], generated_chains=[]):
        if entry["kind"] not in CHAIN_SOURCE_KINDS:
            continue
        if entry.get("event_key") in generated_source_ids:
            continue
        if agent_id is not None and not _entry_involves_agent(entry, agent_id):
            continue
        chain = _derived_chain_for_entry(world, entry, agent_id=agent_id)
        if chain is not None:
            chains.append(chain)

    chains.sort(key=lambda item: (int(item.get("source_day", 0)), str(item.get("id", ""))))
    if limit >= 0:
        chains = chains[-limit:]
    return {
        "kind": "influence_chain_index",
        "version": SOCIAL_TIMELINE_VERSION,
        "day": world.day,
        "agent_id": agent_id,
        "chains": chains,
    }


def _social_entries(
    world: WorldState,
    *,
    dialogue_trace: list[dict[str, Any]],
    generated_chains: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    agents_by_id = {agent.id: agent for agent in world.agents}
    dialogue_lookup = _DialogueTraceLookup(dialogue_trace)
    chain_event_ids = _generated_chain_event_ids(generated_chains)
    entries = []
    for index, event in enumerate(world.event_log):
        if event.kind not in SOCIAL_EVENT_KINDS:
            continue
        trace = dialogue_lookup.match(event)
        participants = _participants_for_event(event, world.agents)
        participant_ids = [agent.id for agent in participants]
        source = _source_for_event(event, trace)
        focus = str(trace.get("focus") or "") if trace else _event_focus(event)
        memory_refs = list(trace.get("memory_refs") or []) if trace else []
        entry_id = _event_id(event, index)
        event_key = _synthetic_event_id(event.day, event.kind, event.actor_id)
        entries.append(
            {
                "id": entry_id,
                "event_key": event_key,
                "day": event.day,
                "kind": event.kind,
                "actor_id": event.actor_id,
                "actor_name": _actor_name(event.actor_id, agents_by_id),
                "participant_ids": participant_ids,
                "participants": [agent.name for agent in participants],
                "summary": event.description,
                "effects": dict(event.effects),
                "source": source,
                "focus": focus,
                "memory_grounded": bool(memory_refs),
                "memory_refs": memory_refs,
                "has_generated_chain": event_key in chain_event_ids,
                "tags": _event_tags(event, focus, source),
            }
        )
    return entries


class _DialogueTraceLookup:
    def __init__(self, trace: list[dict[str, Any]]) -> None:
        self._by_day_actor: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for item in trace:
            try:
                day = int(item.get("day", 0))
            except (TypeError, ValueError):
                continue
            speaker_id = str(item.get("speaker_id", ""))
            self._by_day_actor.setdefault((day, speaker_id), []).append(item)

    def match(self, event: Event) -> dict[str, Any] | None:
        if event.kind != "dialogue":
            return None
        candidates = self._by_day_actor.get((event.day, event.actor_id), [])
        if not candidates:
            return None
        normalized_description = _normalize_text(event.description)
        for candidate in candidates:
            if _normalize_text(candidate.get("used_dialogue")) == normalized_description:
                return candidate
        return candidates[0]


def _source_for_event(event: Event, trace: dict[str, Any] | None) -> str:
    if event.kind != "dialogue":
        return "simulation"
    if trace is None:
        return "rule_or_untraced"
    status = str(trace.get("status") or "")
    if status == "primary":
        return "generated_llm_or_cache"
    if status.startswith("fallback"):
        return "provider_fallback"
    return "rule_fallback"


def _participants_for_event(event: Event, agents: list[Agent]) -> list[Agent]:
    participants: list[Agent] = []
    description = event.description.lower()
    tokens = _terms(event.description)

    if event.kind == "broadcast" and "to everyone" in description:
        return list(agents)

    for agent in agents:
        if agent.id == event.actor_id:
            participants.append(agent)
            continue
        name_terms = _terms(agent.name)
        if agent.id.lower() in tokens or _name_in_text(agent.name, event.description):
            participants.append(agent)
            continue
        if name_terms and name_terms <= tokens:
            participants.append(agent)
    return participants


def _event_focus(event: Event) -> str:
    if event.kind == "broadcast":
        intent_keys = [
            key.removeprefix("intent_")
            for key in event.effects
            if key.startswith("intent_")
        ]
        return intent_keys[0] if intent_keys else "observer_intent"
    if event.kind in {"relationship_crisis", "reconciliation", "mediation"}:
        return "relationship"
    if event.kind in {"organization", "organization_fracture", "institutional_crisis"}:
        return "organization"
    if event.kind in {"route_blocked", "route_reopened"}:
        return "routes"
    return event.kind


def _event_tags(event: Event, focus: str, source: str) -> list[str]:
    tags = {event.kind, focus, source}
    tags.update(str(key) for key in event.effects)
    return sorted(tag for tag in tags if tag)


def _generated_chain_event_ids(items: list[dict[str, Any]]) -> set[str]:
    event_ids = set()
    for item in items:
        try:
            day = int(item.get("dialogue_day", 0))
        except (TypeError, ValueError):
            continue
        speaker_id = str(item.get("speaker_id") or "")
        if day and speaker_id:
            event_ids.add(_synthetic_event_id(day, "dialogue", speaker_id))
    return event_ids


def _chain_from_generated_chain(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        dialogue_day = int(item["dialogue_day"])
    except (KeyError, TypeError, ValueError):
        return None
    speaker_id = str(item.get("speaker_id") or "")
    partner_id = str(item.get("partner_id") or "")
    reflection_agent_id = str(item.get("reflection_agent_id") or "")
    source_event_id = _synthetic_event_id(dialogue_day, "dialogue", speaker_id)
    return {
        "id": f"generated:{dialogue_day}:{speaker_id}:{reflection_agent_id}",
        "kind": "generated_chain",
        "source": "generated_llm_or_cache",
        "source_event_id": source_event_id,
        "source_day": dialogue_day,
        "source_kind": "dialogue",
        "source_text": str(item.get("generated_dialogue") or ""),
        "participant_ids": list(
            dict.fromkeys(
                value
                for value in [speaker_id, partner_id, reflection_agent_id]
                if value
            )
        ),
        "participants": list(
            dict.fromkeys(
                str(value)
                for value in [
                    item.get("speaker_name"),
                    item.get("partner_name"),
                    item.get("reflection_agent_name"),
                ]
                if value
            )
        ),
        "memory_evidence": list(item.get("memory_evidence") or []),
        "reflection_evidence": [
            {
                "day": item.get("reflection_day"),
                "agent_id": reflection_agent_id,
                "agent_name": item.get("reflection_agent_name"),
                "kind": "reflection",
                "text": item.get("generated_reflection"),
                "overlap_terms": list(item.get("shared_terms") or []),
            }
        ],
        "plan_evidence": list(item.get("plan_evidence") or []),
        "baseline_plan_deltas": list(item.get("baseline_plan_deltas") or []),
        "signal": str(item.get("signal") or "generated_chain"),
        "summary": str(item.get("summary") or ""),
    }


def _derived_chain_for_entry(
    world: WorldState,
    entry: dict[str, Any],
    *,
    agent_id: str | None,
) -> dict[str, Any] | None:
    terms = _content_terms(str(entry.get("summary") or ""))
    if not terms:
        return None

    agents_by_id = {agent.id: agent for agent in world.agents}
    participant_ids = list(entry.get("participant_ids") or [])
    if agent_id is not None and agent_id not in participant_ids:
        participant_ids.append(agent_id)
    participant_ids = [
        item
        for item in dict.fromkeys(participant_ids)
        if item in agents_by_id
    ]
    if not participant_ids:
        return None

    source_day = int(entry.get("day", 0))
    memory_evidence = []
    reflection_evidence = []
    plan_evidence = []
    for participant_id in participant_ids:
        agent = agents_by_id[participant_id]
        memory_evidence.extend(
            _memory_evidence(agent, source_day, str(entry.get("kind")), terms)
        )
        reflection_evidence.extend(_reflection_evidence(agent, source_day, terms))
        plan_evidence.extend(_plan_evidence(agent, source_day + 1, world.day, terms))

    memory_evidence = memory_evidence[:6]
    reflection_evidence = reflection_evidence[:6]
    plan_evidence = plan_evidence[:6]
    if not (memory_evidence or reflection_evidence or plan_evidence):
        return None

    signal = _chain_signal(memory_evidence, reflection_evidence, plan_evidence)
    return {
        "id": f"derived:{entry['id']}",
        "kind": "derived_social_chain",
        "source": entry.get("source", "simulation"),
        "source_event_id": entry["id"],
        "source_day": source_day,
        "source_kind": entry.get("kind"),
        "source_text": entry.get("summary"),
        "participant_ids": participant_ids,
        "participants": [
            agents_by_id[participant_id].name
            for participant_id in participant_ids
        ],
        "memory_evidence": memory_evidence,
        "reflection_evidence": reflection_evidence,
        "plan_evidence": plan_evidence,
        "baseline_plan_deltas": [],
        "signal": signal,
        "summary": _derived_chain_summary(
            entry,
            memory_evidence,
            reflection_evidence,
            plan_evidence,
        ),
    }


def _memory_evidence(
    agent: Agent,
    day: int,
    kind: str,
    terms: set[str],
) -> list[dict[str, Any]]:
    evidence = []
    for memory in agent.memory_stream:
        if memory.day != day or memory.kind != kind:
            continue
        overlap = sorted(_terms(memory.text) & terms)
        evidence.append(_memory_item_evidence(agent, memory, overlap))
    return evidence


def _memory_item_evidence(
    agent: Agent,
    memory: MemoryItem,
    overlap_terms: list[str],
) -> dict[str, Any]:
    return {
        "day": memory.day,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "kind": memory.kind,
        "text": memory.text,
        "overlap_terms": overlap_terms,
    }


def _reflection_evidence(
    agent: Agent,
    source_day: int,
    terms: set[str],
) -> list[dict[str, Any]]:
    evidence = []
    for reflection in agent.reflections:
        day = _entry_day(reflection)
        if not source_day <= day <= source_day + 21:
            continue
        overlap = sorted(_terms(reflection) & terms)
        if not overlap:
            continue
        evidence.append(
            {
                "day": day,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "kind": "reflection",
                "text": reflection,
                "overlap_terms": overlap,
            }
        )
    return evidence


def _plan_evidence(
    agent: Agent,
    window_start: int,
    window_end: int,
    terms: set[str],
) -> list[dict[str, Any]]:
    evidence = []
    for entry in agent.plan_history:
        day = _entry_day(entry)
        if not window_start <= day <= window_end:
            continue
        overlap = sorted(_terms(entry) & terms)
        if not overlap:
            continue
        evidence.append(
            {
                "day": day,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "kind": "plan",
                "text": entry,
                "overlap_terms": overlap,
            }
        )
    return evidence


def _chain_signal(
    memories: list[dict[str, Any]],
    reflections: list[dict[str, Any]],
    plans: list[dict[str, Any]],
) -> str:
    if memories and reflections and plans:
        return "social_memory_reflection_plan_echo"
    if memories and plans:
        return "social_memory_plan_echo"
    if memories and reflections:
        return "social_memory_reflection_echo"
    if memories:
        return "social_memory_echo"
    if reflections or plans:
        return "social_downstream_echo"
    return "weak_social_chain"


def _derived_chain_summary(
    entry: dict[str, Any],
    memories: list[dict[str, Any]],
    reflections: list[dict[str, Any]],
    plans: list[dict[str, Any]],
) -> str:
    participants = ", ".join(entry.get("participants") or []) or str(entry.get("actor_name") or "")
    return (
        f"Day {entry.get('day')} {entry.get('kind')} involving {participants} "
        f"left {len(memories)} memory hit(s), {len(reflections)} reflection echo(es), "
        f"and {len(plans)} later plan echo(es)."
    )


def _entry_involves_agent(entry: dict[str, Any], agent_id: str) -> bool:
    return (
        entry.get("actor_id") == agent_id
        or agent_id in {str(value) for value in entry.get("participant_ids", [])}
    )


def _chain_involves_agent(chain: dict[str, Any], agent_id: str) -> bool:
    return agent_id in {str(value) for value in chain.get("participant_ids", [])}


def _find_agent(world: WorldState, agent_id: str) -> Agent | None:
    return next((agent for agent in world.agents if agent.id == agent_id), None)


def _actor_name(actor_id: str, agents_by_id: dict[str, Agent]) -> str:
    agent = agents_by_id.get(actor_id)
    return agent.name if agent is not None else actor_id


def _name_in_text(name: str, text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name.lower())}\b", text.lower()))


def _event_id(event: Event, index: int) -> str:
    synthetic = _synthetic_event_id(event.day, event.kind, event.actor_id)
    return f"{synthetic}:{index}"


def _synthetic_event_id(day: int, kind: str, actor_id: str) -> str:
    return f"day-{day}:{kind}:{actor_id}"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _content_terms(text: str) -> set[str]:
    return _terms(text) - STOP_TERMS


def _terms(text: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if len(term) > 1
    }


def _entry_day(text: str) -> int:
    match = re.search(r"\bday\s+(\d+)\b", text.lower())
    return int(match.group(1)) if match is not None else 0
