from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .model import Event, Location, Organization, WorldState


WORLD_OBJECT_DOSSIER_VERSION = "world-object-dossier-v1"


def build_location_dossiers(
    world: WorldState,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    return {
        "kind": "location_dossier_index",
        "version": WORLD_OBJECT_DOSSIER_VERSION,
        "seed": seed,
        "day": world.day,
        "locations": [
            build_location_dossier(world, location.id, seed=seed)
            for location in world.locations
        ],
    }


def build_location_dossier(
    world: WorldState,
    location_id: str,
    *,
    seed: int | None = None,
    recent_event_limit: int = 12,
) -> dict[str, Any]:
    location = _find_location(world, location_id)
    if location is None:
        raise ValueError(f"unknown location id: {location_id}")
    residents = [
        {"id": agent.id, "name": agent.name, "role": agent.role}
        for agent in world.agents
        if agent.location_id == location.id
    ]
    return {
        "kind": "location_dossier",
        "version": WORLD_OBJECT_DOSSIER_VERSION,
        "seed": seed,
        "day": world.day,
        "location": _location_record(location),
        "continuity": _location_continuity(world, location, residents),
        "recent_events": [
            asdict(event)
            for event in _object_recent_events(
                world.event_log,
                location.id,
                location.name,
                recent_event_limit,
            )
        ],
        "observer_affordances": _location_affordances(world, location),
    }


def build_organization_dossiers(
    world: WorldState,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    return {
        "kind": "organization_dossier_index",
        "version": WORLD_OBJECT_DOSSIER_VERSION,
        "seed": seed,
        "day": world.day,
        "organizations": [
            build_organization_dossier(world, organization.id, seed=seed)
            for organization in world.organizations
        ],
    }


def build_organization_dossier(
    world: WorldState,
    organization_id: str,
    *,
    seed: int | None = None,
    recent_event_limit: int = 12,
) -> dict[str, Any]:
    organization = _find_organization(world, organization_id)
    if organization is None:
        raise ValueError(f"unknown organization id: {organization_id}")
    agents_by_id = {agent.id: agent for agent in world.agents}
    members = [
        {
            "id": member_id,
            "name": agents_by_id[member_id].name if member_id in agents_by_id else member_id,
            "role": agents_by_id[member_id].role if member_id in agents_by_id else "",
        }
        for member_id in organization.members
    ]
    return {
        "kind": "organization_dossier",
        "version": WORLD_OBJECT_DOSSIER_VERSION,
        "seed": seed,
        "day": world.day,
        "organization": _organization_record(organization),
        "continuity": _organization_continuity(world, organization, members),
        "recent_events": [
            asdict(event)
            for event in _object_recent_events(
                world.event_log,
                organization.id,
                organization.name,
                recent_event_limit,
            )
        ],
        "observer_affordances": _organization_affordances(world, organization),
    }


def _location_record(location: Location) -> dict[str, Any]:
    return {
        "id": location.id,
        "name": location.name,
        "kind": location.kind,
        "condition": round(location.condition, 3),
        "capacity": location.capacity,
        "production": {
            key: round(value, 3)
            for key, value in sorted(location.production.items())
        },
        "maintenance_need": round(location.maintenance_need, 3),
        "resources": {
            key: round(value, 3)
            for key, value in sorted(location.resources.items())
        },
        "connected_location_ids": list(location.connected_location_ids),
    }


def _organization_record(organization: Organization) -> dict[str, Any]:
    return {
        "id": organization.id,
        "name": organization.name,
        "kind": organization.kind,
        "home_location_id": organization.home_location_id,
        "members": list(organization.members),
        "norms": list(organization.norms),
        "inventory_targets": {
            key: round(value, 3)
            for key, value in sorted(organization.inventory_targets.items())
        },
        "exchange_preferences": {
            key: round(value, 3)
            for key, value in sorted(organization.exchange_preferences.items())
        },
        "cohesion": round(organization.cohesion, 3),
        "reputation": round(organization.reputation, 3),
    }


def _location_continuity(
    world: WorldState,
    location: Location,
    residents: list[dict[str, str]],
) -> dict[str, Any]:
    route_states = []
    for target_id in location.connected_location_ids:
        route = _route_key(location.id, target_id)
        route_states.append(
            {
                "route": route,
                "target_location_id": target_id,
                "load": round(world.route_loads.get(route, 0.0), 3),
                "blocked": route in world.blocked_routes,
                "repair_need": round(world.blocked_routes.get(route, 0.0), 3),
            }
        )
    return {
        "condition_state": _condition_state(location.condition),
        "resource_pressure": _resource_pressure(location.resources),
        "resident_count": len(residents),
        "residents": residents,
        "connected_routes": sorted(route_states, key=lambda item: item["route"]),
    }


def _organization_continuity(
    world: WorldState,
    organization: Organization,
    members: list[dict[str, str]],
) -> dict[str, Any]:
    home = _find_location(world, organization.home_location_id)
    home_resources = home.resources if home is not None else {}
    inventory_gaps = {
        resource: round(float(target) - float(home_resources.get(resource, 0.0)), 3)
        for resource, target in organization.inventory_targets.items()
    }
    fracture_day = world.organization_fractures.get(organization.id)
    return {
        "cohesion_state": _cohesion_state(organization.cohesion),
        "fractured": fracture_day is not None,
        "fracture_day": fracture_day,
        "member_count": len(members),
        "members": members,
        "home_location": _location_record(home) if home is not None else None,
        "inventory_gaps": inventory_gaps,
    }


def _location_affordances(world: WorldState, location: Location) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    affordances = [
        {
            "id": "support_location_food",
            "label": "Food at Location",
            "description": "Inject bounded food aid at this location.",
            "intervention": {
                "day": next_day,
                "kind": "resource",
                "actor_id": "The_Envoy",
                "reason": f"observer supported {location.name}",
                "params": {
                    "resource": "food",
                    "amount": 4,
                    "location_id": location.id,
                },
            },
        },
        {
            "id": "support_location_materials",
            "label": "Materials at Location",
            "description": "Inject bounded materials at this location.",
            "intervention": {
                "day": next_day,
                "kind": "resource",
                "actor_id": "The_Envoy",
                "reason": f"observer supplied {location.name}",
                "params": {
                    "resource": "materials",
                    "amount": 3,
                    "location_id": location.id,
                },
            },
        },
    ]
    blocked_targets = [
        target_id
        for target_id in location.connected_location_ids
        if _route_key(location.id, target_id) in world.blocked_routes
    ]
    if location.condition < 0.65 or blocked_targets:
        affordances.append(
            {
                "id": "focus_repair_here",
                "label": "Focus Repair",
                "description": "Broadcast a repair intent tied to this location or its blocked routes.",
                "intervention": {
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
                },
            }
        )
    return affordances


def _organization_affordances(
    world: WorldState,
    organization: Organization,
) -> list[dict[str, Any]]:
    next_day = max(1, world.day + 1)
    affordances = [
        {
            "id": "coordinate_members",
            "label": "Coordinate Members",
            "description": "Broadcast a coordination intent to this organization's members.",
            "intervention": {
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
            },
        }
    ]
    if organization.cohesion < 0.52 or organization.id in world.organization_fractures:
        affordances.append(
            {
                "id": "stabilize_organization",
                "label": "Stabilize Organization",
                "description": "Broadcast a stronger stabilization intent to members.",
                "intervention": {
                    "day": next_day,
                    "kind": "broadcast",
                    "actor_id": "The_Envoy",
                    "reason": f"observer stabilized {organization.name}",
                    "params": {
                        "intent": "coordinate",
                        "target_agent_ids": list(organization.members),
                        "tone": "steady",
                        "strength": 0.16,
                        "message": f"Repair trust and keep {organization.name} from fragmenting.",
                    },
                },
            }
        )
    return affordances


def _object_recent_events(
    events: list[Event],
    object_id: str,
    object_name: str,
    limit: int,
) -> list[Event]:
    normalized_id = object_id.replace("_", " ").lower()
    normalized_name = object_name.lower()
    matched = [
        event
        for event in events
        if event.actor_id == object_id
        or normalized_id in event.description.lower()
        or normalized_name in event.description.lower()
    ]
    return matched[-max(0, limit):]


def _resource_pressure(resources: dict[str, float]) -> list[str]:
    pressure = []
    if resources.get("food", 0.0) < 1.0:
        pressure.append("food_low")
    if resources.get("materials", 0.0) < 1.0:
        pressure.append("materials_low")
    if resources.get("shelter", 0.0) < 1.0:
        pressure.append("shelter_low")
    return pressure


def _condition_state(condition: float) -> str:
    if condition < 0.35:
        return "damaged"
    if condition < 0.65:
        return "strained"
    return "stable"


def _cohesion_state(cohesion: float) -> str:
    if cohesion < 0.35:
        return "fracture_risk"
    if cohesion < 0.52:
        return "strained"
    return "stable"


def _repair_agent_ids(world: WorldState, limit: int = 3) -> list[str]:
    ranked = sorted(
        world.agents,
        key=lambda agent: (
            agent.skills.get("building", 0.0),
            agent.skills.get("logistics", 0.0),
            agent.reputation,
        ),
        reverse=True,
    )
    return [agent.id for agent in ranked[:limit]]


def _find_location(world: WorldState, location_id: str) -> Location | None:
    for location in world.locations:
        if location.id == location_id:
            return location
    return None


def _find_organization(
    world: WorldState,
    organization_id: str,
) -> Organization | None:
    for organization in world.organizations:
        if organization.id == organization_id:
            return organization
    return None


def _route_key(first_location_id: str, second_location_id: str) -> str:
    left, right = sorted([first_location_id, second_location_id])
    return f"{left}|{right}"
