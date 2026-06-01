from __future__ import annotations

import math
from typing import Any

from .agent_dossiers import build_relationship_links
from .model import Agent, Location, Organization, Plan, WorldState
from .social_timeline import build_social_feed


WORLD_CLIENT_PROTOCOL_VERSION = "world-client-v1"


def build_world_client_frame(
    world: WorldState,
    *,
    seed: int | None = None,
    world_preset: str | None = None,
    provider_status: dict[str, Any] | None = None,
    social_feed: dict[str, Any] | None = None,
    social_limit: int = 30,
) -> dict[str, Any]:
    """Build a read-optimized frame for external world clients.

    The frame is deliberately made of JSON primitives and bounded command
    payloads. Clients can render it directly, but state changes still go through
    the intervention API.
    """

    positions = _location_positions(world.locations)
    relationship_links = build_relationship_links(world)
    feed = social_feed or build_social_feed(world, limit=social_limit)
    locations = [
        _location_frame(world, location, positions[location.id])
        for location in sorted(world.locations, key=lambda item: item.id)
    ]
    routes = _route_frames(world, positions)
    agents = _agent_frames(world, positions, relationship_links)
    organizations = [
        _organization_frame(world, organization)
        for organization in sorted(world.organizations, key=lambda item: item.id)
    ]
    affordances = [
        *_global_affordances(world),
        *[
            affordance
            for location in locations
            for affordance in location["affordances"]
        ],
        *[
            affordance
            for agent in agents
            for affordance in agent["affordances"]
        ],
        *[
            affordance
            for organization in organizations
            for affordance in organization["affordances"]
        ],
    ]
    social_entries = list(feed.get("entries", []))
    if social_limit >= 0:
        social_entries = social_entries[-social_limit:]
    return {
        "kind": "world_client_frame",
        "version": WORLD_CLIENT_PROTOCOL_VERSION,
        "seed": seed,
        "world_preset": world_preset,
        "day": world.day,
        "coordinate_system": {
            "kind": "client_cartesian",
            "units": "abstract_meters",
            "up_axis": "y",
            "origin_location_id": "commons",
        },
        "provider": _provider_frame(provider_status),
        "metrics": _metrics_frame(world),
        "resources": _round_dict(world.resources),
        "locations": locations,
        "routes": routes,
        "agents": agents,
        "organizations": organizations,
        "social_feed": social_entries,
        "affordances": affordances,
        "read_endpoints": {
            "state": "/state",
            "social_feed": "/social-feed",
            "agents": "/agents",
            "locations": "/locations",
            "organizations": "/organizations",
        },
        "command_endpoints": {
            "step": "/step",
            "interventions": "/interventions",
            "reset": "/reset",
        },
    }


def _location_frame(
    world: WorldState,
    location: Location,
    position: dict[str, float],
) -> dict[str, Any]:
    residents = [
        {"id": agent.id, "name": agent.name, "role": agent.role}
        for agent in sorted(world.agents, key=lambda item: item.id)
        if agent.location_id == location.id
    ]
    connected_route_ids = [
        _route_key(location.id, target_id)
        for target_id in sorted(location.connected_location_ids)
    ]
    return {
        "id": location.id,
        "name": location.name,
        "kind": location.kind,
        "position": dict(position),
        "condition": round(location.condition, 3),
        "condition_state": _condition_state(location.condition),
        "capacity": location.capacity,
        "resources": _round_dict(location.resources),
        "production": _round_dict(location.production),
        "maintenance_need": round(location.maintenance_need, 3),
        "resident_count": len(residents),
        "residents": residents,
        "connected_route_ids": connected_route_ids,
        "visual": {
            "shape": "location_node",
            "color": _location_color(location.kind, location.condition),
            "scale": round(0.85 + min(len(residents), 8) * 0.05, 3),
            "label": location.name,
        },
        "affordances": _location_affordances(world, location),
        "inspect_url": f"/locations/{location.id}",
    }


def _route_frames(
    world: WorldState,
    positions: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    routes = []
    seen: set[str] = set()
    locations_by_id = {location.id: location for location in world.locations}
    for location in sorted(world.locations, key=lambda item: item.id):
        for target_id in sorted(location.connected_location_ids):
            if target_id not in positions:
                continue
            route_id = _route_key(location.id, target_id)
            if route_id in seen:
                continue
            seen.add(route_id)
            target = locations_by_id.get(target_id)
            condition = _route_condition(location, target)
            blocked = route_id in world.blocked_routes
            load = round(world.route_loads.get(route_id, 0.0), 3)
            routes.append(
                {
                    "id": route_id,
                    "source_location_id": location.id,
                    "target_location_id": target_id,
                    "points": [positions[location.id], positions[target_id]],
                    "load": load,
                    "condition": condition,
                    "blocked": blocked,
                    "repair_need": round(world.blocked_routes.get(route_id, 0.0), 3),
                    "visual": {
                        "shape": "route_path",
                        "color": "#a33232" if blocked else _route_color(load, condition),
                        "width": round(0.05 + min(load, 6.0) * 0.018, 3),
                        "style": "blocked" if blocked else "open",
                    },
                    "affordances": _route_affordances(world, route_id, location.id, target_id),
                }
            )
    return routes


def _agent_frames(
    world: WorldState,
    positions: dict[str, dict[str, float]],
    relationship_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_location_index: dict[str, int] = {}
    by_location_count: dict[str, int] = {}
    for agent in world.agents:
        by_location_count[agent.location_id] = by_location_count.get(agent.location_id, 0) + 1

    frames = []
    for agent in sorted(world.agents, key=lambda item: item.id):
        index = by_location_index.get(agent.location_id, 0)
        by_location_index[agent.location_id] = index + 1
        location_position = positions.get(agent.location_id, {"x": 0.0, "y": 0.0, "z": 0.0})
        count = max(1, by_location_count.get(agent.location_id, 1))
        position = _agent_position(location_position, index, count)
        links = [
            link
            for link in relationship_links
            if agent.id in {str(value) for value in link.get("agent_ids", [])}
        ]
        crisis_count = sum(1 for link in links if link.get("crisis"))
        return_plan = _plan_frame(agent.active_plan)
        frames.append(
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "location_id": agent.location_id,
                "position": position,
                "needs": _round_dict(vars(agent.needs)),
                "average_need": round(agent.needs.average(), 3),
                "reputation": round(agent.reputation, 3),
                "average_trust": _average(agent.relationships.values()),
                "relationship_crisis_count": crisis_count,
                "organization_ids": list(agent.organization_ids),
                "active_plan": return_plan,
                "recent_memory": agent.memory_stream[-1].text if agent.memory_stream else "",
                "latest_reflection": agent.reflections[-1] if agent.reflections else "",
                "visual": {
                    "shape": "agent_marker",
                    "color": _need_color(agent.needs.average(), crisis_count),
                    "scale": round(0.85 + agent.reputation * 0.22, 3),
                    "label": agent.name,
                    "status": _agent_status(agent.needs.average(), crisis_count),
                },
                "affordances": _agent_affordances(world, agent),
                "inspect_url": f"/agents/{agent.id}",
                "social_history_url": f"/agents/{agent.id}/social-history",
            }
        )
    return frames


def _organization_frame(
    world: WorldState,
    organization: Organization,
) -> dict[str, Any]:
    home_location = _find_location(world, organization.home_location_id)
    fractured = organization.id in world.organization_fractures
    return {
        "id": organization.id,
        "name": organization.name,
        "kind": organization.kind,
        "home_location_id": organization.home_location_id,
        "member_ids": list(organization.members),
        "norms": list(organization.norms),
        "cohesion": round(organization.cohesion, 3),
        "reputation": round(organization.reputation, 3),
        "fractured": fractured,
        "fracture_day": world.organization_fractures.get(organization.id),
        "inventory_targets": _round_dict(organization.inventory_targets),
        "inventory_gaps": _inventory_gaps(organization, home_location),
        "visual": {
            "shape": "organization_ring",
            "color": "#a33232" if fractured else _cohesion_color(organization.cohesion),
            "scale": round(0.7 + max(1, len(organization.members)) * 0.05, 3),
            "label": organization.name,
        },
        "affordances": _organization_affordances(world, organization),
        "inspect_url": f"/organizations/{organization.id}",
    }


def _provider_frame(provider_status: dict[str, Any] | None) -> dict[str, Any]:
    if not provider_status:
        return {
            "live_llm_enabled": False,
            "models": [],
            "surfaces": {},
        }
    return {
        "live_llm_enabled": bool(provider_status.get("live_llm_enabled")),
        "models": list(provider_status.get("models") or []),
        "surfaces": {
            key: {
                "mode": value.get("mode"),
                "provider": value.get("provider"),
                "primary_provider": value.get("primary_provider"),
                "model": value.get("model"),
                "trace_length": value.get("trace_length", 0),
                "stats": dict(value.get("stats") or {}),
            }
            for key, value in sorted((provider_status.get("surfaces") or {}).items())
            if isinstance(value, dict)
        },
    }


def _global_affordances(world: WorldState) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    return [
        {
            "id": "global_step_1_day",
            "target_kind": "world",
            "target_id": "world",
            "label": "Step 1 Day",
            "method": "POST",
            "endpoint": "/step",
            "payload": {"days": 1, "interventions": []},
        },
        {
            "id": "global_coordinate_broadcast",
            "target_kind": "world",
            "target_id": "world",
            "label": "Broadcast Coordination",
            "method": "POST",
            "endpoint": "/step",
            "payload": {
                "days": 1,
                "interventions": [
                    {
                        "day": next_day,
                        "kind": "broadcast",
                        "actor_id": "The_Envoy",
                        "reason": "observer coordinated the society",
                        "params": {
                            "intent": "coordinate",
                            "tone": "steady",
                            "strength": 0.10,
                            "message": "Coordinate openly before small failures become shared crises.",
                        },
                    }
                ],
            },
        },
    ]


def _agent_affordances(world: WorldState, agent: Agent) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    return [
        {
            "id": f"agent:{agent.id}:inspect",
            "target_kind": "agent",
            "target_id": agent.id,
            "label": "Inspect Agent",
            "method": "GET",
            "endpoint": f"/agents/{agent.id}",
        },
        {
            "id": f"agent:{agent.id}:social_history",
            "target_kind": "agent",
            "target_id": agent.id,
            "label": "Social History",
            "method": "GET",
            "endpoint": f"/agents/{agent.id}/social-history",
        },
        {
            "id": f"agent:{agent.id}:broadcast_intent",
            "target_kind": "agent",
            "target_id": agent.id,
            "label": "Broadcast Intent",
            "method": "POST",
            "endpoint": "/step",
            "payload": {
                "days": 1,
                "interventions": [
                    {
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
                    }
                ],
            },
        },
    ]


def _location_affordances(world: WorldState, location: Location) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    affordances = [
        {
            "id": f"location:{location.id}:inspect",
            "target_kind": "location",
            "target_id": location.id,
            "label": "Inspect Location",
            "method": "GET",
            "endpoint": f"/locations/{location.id}",
        },
        {
            "id": f"location:{location.id}:food",
            "target_kind": "location",
            "target_id": location.id,
            "label": "Food at Location",
            "method": "POST",
            "endpoint": "/step",
            "payload": {
                "days": 1,
                "interventions": [
                    {
                        "day": next_day,
                        "kind": "resource",
                        "actor_id": "The_Envoy",
                        "reason": f"observer supported {location.name}",
                        "params": {
                            "resource": "food",
                            "amount": 4,
                            "location_id": location.id,
                        },
                    }
                ],
            },
        },
    ]
    if location.condition < 0.65 or any(
        _route_key(location.id, target_id) in world.blocked_routes
        for target_id in location.connected_location_ids
    ):
        affordances.append(
            {
                "id": f"location:{location.id}:repair_broadcast",
                "target_kind": "location",
                "target_id": location.id,
                "label": "Focus Repair",
                "method": "POST",
                "endpoint": "/step",
                "payload": {
                    "days": 1,
                    "interventions": [
                        {
                            "day": next_day,
                            "kind": "broadcast",
                            "actor_id": "The_Envoy",
                            "reason": f"observer focused repair at {location.name}",
                            "params": {
                                "intent": "repair_routes",
                                "target_agent_ids": _repair_agent_ids(world),
                                "tone": "practical",
                                "strength": 0.12,
                                "message": f"Prioritize repair work around {location.name}.",
                            },
                        }
                    ],
                },
            }
        )
    return affordances


def _route_affordances(
    world: WorldState,
    route_id: str,
    source_location_id: str,
    target_location_id: str,
) -> list[dict[str, Any]]:
    if route_id not in world.blocked_routes:
        return []
    next_day = max(1, world.day + 1)
    return [
        {
            "id": f"route:{route_id}:repair_broadcast",
            "target_kind": "route",
            "target_id": route_id,
            "label": "Broadcast Route Repair",
            "method": "POST",
            "endpoint": "/step",
            "payload": {
                "days": 1,
                "interventions": [
                    {
                        "day": next_day,
                        "kind": "broadcast",
                        "actor_id": "The_Envoy",
                        "reason": f"observer focused route repair {route_id}",
                        "params": {
                            "intent": "repair_routes",
                            "target_agent_ids": _repair_agent_ids(world),
                            "tone": "practical",
                            "strength": 0.14,
                            "message": (
                                f"Reopen the route between {source_location_id} "
                                f"and {target_location_id} before more hauling."
                            ),
                        },
                    }
                ],
            },
        }
    ]


def _organization_affordances(
    world: WorldState,
    organization: Organization,
) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    return [
        {
            "id": f"organization:{organization.id}:inspect",
            "target_kind": "organization",
            "target_id": organization.id,
            "label": "Inspect Organization",
            "method": "GET",
            "endpoint": f"/organizations/{organization.id}",
        },
        {
            "id": f"organization:{organization.id}:coordinate",
            "target_kind": "organization",
            "target_id": organization.id,
            "label": "Coordinate Members",
            "method": "POST",
            "endpoint": "/step",
            "payload": {
                "days": 1,
                "interventions": [
                    {
                        "day": next_day,
                        "kind": "broadcast",
                        "actor_id": "The_Envoy",
                        "reason": f"observer coordinated {organization.name}",
                        "params": {
                            "intent": "coordinate",
                            "target_agent_ids": list(organization.members),
                            "tone": "steady",
                            "strength": 0.10,
                            "message": f"Coordinate through {organization.name}'s norms and current responsibilities.",
                        },
                    }
                ],
            },
        },
    ]


def _location_positions(locations: list[Location]) -> dict[str, dict[str, float]]:
    if not locations:
        return {}
    positions: dict[str, dict[str, float]] = {}
    if any(location.id == "commons" for location in locations):
        positions["commons"] = _position(0.0, 0.0, 0.0)
    ring = [
        location
        for location in sorted(locations, key=lambda item: item.id)
        if location.id != "commons"
    ]
    radius = 9.5 if len(ring) > 4 else 7.0
    for index, location in enumerate(ring):
        angle = (math.tau * index / max(1, len(ring))) - math.pi / 2
        positions[location.id] = _position(
            math.cos(angle) * radius,
            0.0,
            math.sin(angle) * radius,
        )
    if "commons" not in positions:
        first = sorted(locations, key=lambda item: item.id)[0]
        positions[first.id] = _position(0.0, 0.0, 0.0)
    return positions


def _agent_position(
    location_position: dict[str, float],
    index: int,
    count: int,
) -> dict[str, float]:
    angle = (math.tau * index / max(1, count)) - math.pi / 2
    radius = 1.1 + min(count, 8) * 0.08
    return _position(
        float(location_position["x"]) + math.cos(angle) * radius,
        0.8,
        float(location_position["z"]) + math.sin(angle) * radius,
    )


def _metrics_frame(world: WorldState) -> dict[str, Any]:
    agents = world.agents
    organizations = world.organizations
    return {
        "population": len(agents),
        "average_need": _average(agent.needs.average() for agent in agents),
        "average_trust": _average(
            trust
            for agent in agents
            for trust in agent.relationships.values()
        ),
        "average_reputation": _average(agent.reputation for agent in agents),
        "institutional_cohesion": _average(
            organization.cohesion
            for organization in organizations
        ),
        "active_relationship_crises": len(world.relationship_crises),
        "active_blocked_routes": len(world.blocked_routes),
        "active_organization_fractures": len(world.organization_fractures),
    }


def _inventory_gaps(
    organization: Organization,
    home_location: Location | None,
) -> dict[str, float]:
    resources = home_location.resources if home_location is not None else {}
    return {
        resource: round(float(target) - float(resources.get(resource, 0.0)), 3)
        for resource, target in sorted(organization.inventory_targets.items())
    }


def _plan_frame(plan: Plan | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "action": plan.action.value,
        "priority": round(plan.priority, 3),
        "reason": plan.reason,
        "target_id": plan.target_id,
        "horizon_days": plan.horizon_days,
    }


def _repair_agent_ids(world: WorldState, limit: int = 3) -> list[str]:
    ranked = sorted(
        world.agents,
        key=lambda agent: (
            agent.skills.get("building", 0.0),
            agent.skills.get("logistics", 0.0),
            agent.reputation,
            agent.id,
        ),
        reverse=True,
    )
    return [agent.id for agent in ranked[:limit]]


def _find_location(world: WorldState, location_id: str) -> Location | None:
    return next((location for location in world.locations if location.id == location_id), None)


def _route_condition(first: Location, second: Location | None) -> float:
    if second is None:
        return round(first.condition, 3)
    return round((first.condition + second.condition) / 2, 3)


def _condition_state(condition: float) -> str:
    if condition < 0.35:
        return "damaged"
    if condition < 0.65:
        return "strained"
    return "stable"


def _agent_status(average_need: float, crisis_count: int) -> str:
    if crisis_count:
        return "social_crisis"
    if average_need < 0.42:
        return "strained"
    if average_need < 0.62:
        return "watch"
    return "stable"


def _need_color(average_need: float, crisis_count: int) -> str:
    if crisis_count:
        return "#a33232"
    if average_need < 0.42:
        return "#d16d6d"
    if average_need < 0.62:
        return "#d49b4a"
    return "#4fb58f"


def _location_color(kind: str, condition: float) -> str:
    if condition < 0.35:
        return "#a33232"
    colors = {
        "farm": "#4f8f5f",
        "wildland": "#6f8c56",
        "production": "#d49b4a",
        "dwelling": "#6aa3d8",
        "civic": "#5b7f78",
    }
    return colors.get(kind, "#5b7f78")


def _route_color(load: float, condition: float) -> str:
    if condition < 0.35:
        return "#d49b4a"
    if load > 4:
        return "#a15c12"
    return "#436f76"


def _cohesion_color(cohesion: float) -> str:
    if cohesion < 0.35:
        return "#a33232"
    if cohesion < 0.52:
        return "#d49b4a"
    return "#6aa3d8"


def _round_dict(values: dict[str, float]) -> dict[str, float]:
    return {
        str(key): round(float(value), 3)
        for key, value in sorted(values.items())
    }


def _average(values: Any) -> float:
    items = [float(value) for value in values]
    if not items:
        return 0.0
    return round(sum(items) / len(items), 3)


def _position(x: float, y: float, z: float) -> dict[str, float]:
    return {
        "x": round(x, 3),
        "y": round(y, 3),
        "z": round(z, 3),
    }


def _route_key(first_location_id: str, second_location_id: str) -> str:
    left, right = sorted([first_location_id, second_location_id])
    return f"{left}|{right}"
