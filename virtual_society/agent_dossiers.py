from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .model import Agent, Event, Plan, WorldState


AGENT_DOSSIER_VERSION = "agent-dossier-v1"


def build_agent_record(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "location_id": agent.location_id,
        "profile": asdict(agent.profile),
        "needs": asdict(agent.needs),
        "skills": {
            key: round(value, 3)
            for key, value in sorted(agent.skills.items())
        },
        "average_need": round(agent.needs.average(), 3),
        "average_trust": _average(agent.relationships.values()),
        "reputation": round(agent.reputation, 3),
        "organization_ids": list(agent.organization_ids),
        "active_plan": _plan_dict(agent.active_plan),
        "recent_memories": agent.memories[-5:],
        "recent_memory_stream": [
            asdict(memory)
            for memory in agent.memory_stream[-5:]
        ],
        "recent_reflections": agent.reflections[-3:],
        "recent_life_journal": [
            asdict(item)
            for item in agent.life_journal[-5:]
        ],
    }


def build_relationship_links(world: WorldState) -> list[dict[str, Any]]:
    agents_by_id = {agent.id: agent for agent in world.agents}
    links = []
    seen_pairs: set[str] = set()
    for agent in world.agents:
        for other_id, trust in agent.relationships.items():
            other = agents_by_id.get(other_id)
            if other is None:
                continue
            pair_key = _agent_pair_key(agent.id, other.id)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            reciprocal = other.relationships.get(agent.id, trust)
            crisis_day = world.relationship_crises.get(pair_key)
            links.append(
                {
                    "pair": pair_key,
                    "agent_ids": pair_key.split("|"),
                    "agents": [
                        agents_by_id[agent_id].name
                        if agent_id in agents_by_id
                        else agent_id
                        for agent_id in pair_key.split("|")
                    ],
                    "average_trust": round((float(trust) + float(reciprocal)) / 2, 3),
                    "crisis": crisis_day is not None,
                    "started_day": crisis_day,
                }
            )
    return sorted(
        links,
        key=lambda item: (
            not bool(item["crisis"]),
            float(item["average_trust"]),
            str(item["pair"]),
        ),
    )


def build_agent_dossiers(
    world: WorldState,
    *,
    seed: int | None = None,
    observer_recommendations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    relationship_links = build_relationship_links(world)
    recommendations = observer_recommendations or []
    return {
        "kind": "agent_dossier_index",
        "version": AGENT_DOSSIER_VERSION,
        "seed": seed,
        "day": world.day,
        "agents": [
            build_agent_dossier(
                world,
                agent.id,
                seed=seed,
                relationship_links=relationship_links,
                observer_recommendations=recommendations,
            )
            for agent in world.agents
        ],
    }


def build_agent_dossier(
    world: WorldState,
    agent_id: str,
    *,
    seed: int | None = None,
    relationship_links: list[dict[str, Any]] | None = None,
    observer_recommendations: list[dict[str, Any]] | None = None,
    recent_event_limit: int = 12,
) -> dict[str, Any]:
    agent = _find_agent(world, agent_id)
    if agent is None:
        raise ValueError(f"unknown agent id: {agent_id}")

    links = [
        item
        for item in (relationship_links or build_relationship_links(world))
        if agent_id in {str(value) for value in item.get("agent_ids", [])}
    ]
    recent_events = [
        asdict(event)
        for event in _agent_recent_events(world.event_log, agent_id, recent_event_limit)
    ]
    recommendations = list(observer_recommendations or [])
    return {
        "kind": "agent_dossier",
        "version": AGENT_DOSSIER_VERSION,
        "seed": seed,
        "day": world.day,
        "agent": build_agent_record(agent),
        "continuity": _continuity(agent, links),
        "relationship_links": links,
        "recent_events": recent_events,
        "relevant_observer_recommendations": [
            item
            for item in recommendations
            if _recommendation_targets_agent(item, agent_id)
        ],
        "observer_recommendations": recommendations,
        "observer_affordances": _observer_affordances(world, agent, links),
    }


def _continuity(agent: Agent, relationship_links: list[dict[str, Any]]) -> dict[str, Any]:
    latest_life = asdict(agent.life_journal[-1]) if agent.life_journal else None
    latest_memory = asdict(agent.memory_stream[-1]) if agent.memory_stream else None
    latest_reflection = agent.reflections[-1] if agent.reflections else None
    weakest_link = (
        min(relationship_links, key=lambda item: float(item.get("average_trust", 1.0)))
        if relationship_links
        else None
    )
    return {
        "identity": {
            "background": agent.profile.background,
            "values": list(agent.profile.values),
            "long_term_goals": list(agent.profile.long_term_goals),
            "speech_style": agent.profile.speech_style,
        },
        "current_plan": _plan_dict(agent.active_plan),
        "latest_life_episode": latest_life,
        "latest_memory": latest_memory,
        "latest_reflection": latest_reflection,
        "pressure_tags": _pressure_tags(agent, relationship_links),
        "social_state": {
            "relationship_crisis_count": sum(
                1 for item in relationship_links if item.get("crisis")
            ),
            "weakest_relationship": weakest_link,
            "average_trust": _average(agent.relationships.values()),
        },
    }


def _pressure_tags(agent: Agent, relationship_links: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    needs = agent.needs
    low_need_thresholds = {
        "food_pressure": needs.food,
        "energy_pressure": needs.energy,
        "safety_pressure": needs.safety,
        "belonging_pressure": needs.belonging,
        "meaning_pressure": needs.meaning,
    }
    tags.extend(
        label
        for label, value in low_need_thresholds.items()
        if value < 0.45
    )
    if agent.life_journal:
        for pressure in agent.life_journal[-1].pressures:
            if pressure not in tags:
                tags.append(pressure)
    if any(item.get("crisis") for item in relationship_links):
        tags.append("relationship_crisis")
    if agent.active_plan is not None:
        tags.append(f"plan_{agent.active_plan.action.value}")
    return tags[:8]


def _observer_affordances(
    world: WorldState,
    agent: Agent,
    relationship_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    affordances = [
        {
            "id": "broadcast_intent",
            "label": "Broadcast Intent",
            "description": "Write a targeted observer intent into this agent's memory.",
            "intervention": {
                "day": next_day,
                "kind": "broadcast",
                "actor_id": "The_Envoy",
                "reason": f"observer targeted {agent.name}",
                "params": {
                    "intent": "coordinate",
                    "target_agent_ids": [agent.id],
                    "tone": "steady",
                    "strength": 0.10,
                    "message": "Name the current pressure and coordinate with the people affected by it.",
                },
            },
        },
        {
            "id": "support_location_food",
            "label": "Food at Location",
            "description": "Inject bounded food aid at the selected agent's current location.",
            "intervention": {
                "day": next_day,
                "kind": "resource",
                "actor_id": "The_Envoy",
                "reason": f"observer supported {agent.name}'s location",
                "params": {
                    "resource": "food",
                    "amount": 4,
                    "location_id": agent.location_id,
                },
            },
        },
    ]
    crisis = next((item for item in relationship_links if item.get("crisis")), None)
    if crisis:
        affordances.insert(
            1,
            {
                "id": "mediate_crisis",
                "label": "Mediate Crisis",
                "description": "Trigger a bounded mediation for this agent's active relationship crisis.",
                "intervention": {
                    "day": next_day,
                    "kind": "mediation",
                    "actor_id": "The_Envoy",
                    "reason": f"observer mediated {crisis.get('pair', agent.id)}",
                    "params": {
                        "target_agent_ids": list(crisis.get("agent_ids") or [agent.id]),
                        "message": "Name the grievance and rebuild a practical agreement.",
                    },
                },
            },
        )
    return affordances


def _agent_recent_events(
    events: list[Event],
    agent_id: str,
    limit: int,
) -> list[Event]:
    return [
        event
        for event in events
        if event.actor_id == agent_id
    ][-max(0, limit):]


def _recommendation_targets_agent(item: dict[str, Any], agent_id: str) -> bool:
    intervention = item.get("intervention")
    if not isinstance(intervention, dict):
        return False
    params = intervention.get("params")
    if not isinstance(params, dict):
        return False
    target_agent_ids = params.get("target_agent_ids")
    if not isinstance(target_agent_ids, list):
        return False
    return agent_id in {str(value) for value in target_agent_ids}


def _find_agent(world: WorldState, agent_id: str) -> Agent | None:
    for agent in world.agents:
        if agent.id == agent_id:
            return agent
    return None


def _average(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(float(item) for item in items) / len(items), 3)


def _plan_dict(plan: Plan | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "action": plan.action.value,
        "priority": plan.priority,
        "reason": plan.reason,
        "target_id": plan.target_id,
        "horizon_days": plan.horizon_days,
    }


def _agent_pair_key(first_agent_id: str, second_agent_id: str) -> str:
    left, right = sorted([first_agent_id, second_agent_id], key=_agent_sort_key)
    return f"{left}|{right}"


def _agent_sort_key(agent_id: str) -> tuple[str, int | str]:
    if len(agent_id) > 1 and agent_id[0].isalpha() and agent_id[1:].isdigit():
        return (agent_id[0], int(agent_id[1:]))
    return (agent_id, agent_id)
