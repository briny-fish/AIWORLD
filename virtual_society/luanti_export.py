from __future__ import annotations

from typing import Any


LUANTI_SCENE_VERSION = "luanti-scene-v1"


def build_luanti_scene(
    frame: dict[str, Any],
    *,
    scale: float = 2.0,
    max_social_entries: int = 8,
) -> dict[str, Any]:
    """Convert a world-client-v1 frame into a Luanti-friendly scene package."""

    locations = list(frame.get("locations") or [])
    routes = list(frame.get("routes") or [])
    agents = list(frame.get("agents") or [])
    organizations = list(frame.get("organizations") or [])
    nodes = [
        _location_node(location, scale)
        for location in locations
    ]
    route_nodes = [
        node
        for route in routes
        for node in _route_nodes(route, scale)
    ]
    organization_nodes = [
        _organization_node(organization, locations, index, scale)
        for index, organization in enumerate(organizations)
    ]
    entity_frames = [
        _agent_entity(agent, scale)
        for agent in agents
    ]
    social_entries = list(frame.get("social_feed") or [])[-max_social_entries:]

    return {
        "kind": "luanti_scene",
        "version": LUANTI_SCENE_VERSION,
        "source": {
            "kind": frame.get("kind"),
            "version": frame.get("version"),
            "day": frame.get("day"),
            "seed": frame.get("seed"),
            "world_preset": frame.get("world_preset"),
        },
        "scale": scale,
        "materials": _materials(),
        "nodes": [*nodes, *route_nodes, *organization_nodes],
        "entities": entity_frames,
        "social_log": [
            {
                "day": entry.get("day"),
                "kind": entry.get("kind"),
                "title": entry.get("title") or entry.get("summary") or "",
                "summary": entry.get("summary") or entry.get("description") or "",
                "participants": list(entry.get("participants") or []),
            }
            for entry in social_entries
        ],
        "api": {
            "read_endpoints": dict(frame.get("read_endpoints") or {}),
            "command_endpoints": dict(frame.get("command_endpoints") or {}),
            "affordance_count": len(frame.get("affordances") or []),
        },
    }


def _location_node(location: dict[str, Any], scale: float) -> dict[str, Any]:
    condition_state = str(location.get("condition_state") or "stable")
    kind = str(location.get("kind") or "civic")
    node = _location_node_name(kind)
    if condition_state == "damaged":
        node = "aiworld_bridge:location_damaged"
    return {
        "kind": "location",
        "id": location.get("id"),
        "name": location.get("name") or location.get("id"),
        "node": node,
        "pos": _to_luanti_block(location.get("position") or {}, scale, y=0),
        "label": location.get("name") or location.get("id"),
        "condition": location.get("condition"),
        "resources": dict(location.get("resources") or {}),
    }


def _route_nodes(route: dict[str, Any], scale: float) -> list[dict[str, Any]]:
    points = list(route.get("points") or [])
    if len(points) < 2:
        return []
    start = _to_luanti_block(points[0], scale, y=0)
    end = _to_luanti_block(points[-1], scale, y=0)
    node_name = "aiworld_bridge:route_blocked" if route.get("blocked") else "aiworld_bridge:route_open"
    blocks = []
    for pos in _line_blocks(start, end):
        blocks.append(
            {
                "kind": "route",
                "id": route.get("id"),
                "node": node_name,
                "pos": pos,
                "blocked": bool(route.get("blocked")),
                "repair_need": route.get("repair_need", 0.0),
            }
        )
    return blocks


def _organization_node(
    organization: dict[str, Any],
    locations: list[dict[str, Any]],
    index: int,
    scale: float,
) -> dict[str, Any]:
    home_id = organization.get("home_location_id")
    home = next((location for location in locations if location.get("id") == home_id), None)
    base = _to_luanti_block((home or {}).get("position") or {}, scale, y=1)
    return {
        "kind": "organization",
        "id": organization.get("id"),
        "name": organization.get("name") or organization.get("id"),
        "node": (
            "aiworld_bridge:organization_fractured"
            if organization.get("fractured")
            else "aiworld_bridge:organization"
        ),
        "pos": {"x": base["x"] + index + 1, "y": base["y"], "z": base["z"] + index + 1},
        "cohesion": organization.get("cohesion"),
        "member_ids": list(organization.get("member_ids") or []),
    }


def _agent_entity(agent: dict[str, Any], scale: float) -> dict[str, Any]:
    visual = dict(agent.get("visual") or {})
    return {
        "kind": "agent",
        "id": agent.get("id"),
        "name": agent.get("name") or agent.get("id"),
        "role": agent.get("role"),
        "entity": "aiworld_bridge:agent_marker",
        "pos": _to_luanti_float(agent.get("position") or {}, scale),
        "status": visual.get("status") or "stable",
        "color": visual.get("color") or "#eef5f2",
        "active_plan": agent.get("active_plan"),
        "recent_memory": agent.get("recent_memory") or "",
    }


def _materials() -> dict[str, dict[str, str]]:
    return {
        "aiworld_bridge:location_civic": {"color": "#5b7f78", "label": "civic"},
        "aiworld_bridge:location_dwelling": {"color": "#6aa3d8", "label": "dwelling"},
        "aiworld_bridge:location_farm": {"color": "#4f8f5f", "label": "farm"},
        "aiworld_bridge:location_production": {"color": "#d49b4a", "label": "production"},
        "aiworld_bridge:location_wildland": {"color": "#6f8c56", "label": "wildland"},
        "aiworld_bridge:location_damaged": {"color": "#a33232", "label": "damaged location"},
        "aiworld_bridge:route_open": {"color": "#436f76", "label": "open route"},
        "aiworld_bridge:route_blocked": {"color": "#a33232", "label": "blocked route"},
        "aiworld_bridge:organization": {"color": "#6aa3d8", "label": "organization"},
        "aiworld_bridge:organization_fractured": {"color": "#d16d6d", "label": "fractured organization"},
    }


def _location_node_name(kind: str) -> str:
    known = {"civic", "dwelling", "farm", "production", "wildland"}
    if kind not in known:
        return "aiworld_bridge:location_civic"
    return f"aiworld_bridge:location_{kind}"


def _to_luanti_block(position: dict[str, Any], scale: float, *, y: int) -> dict[str, int]:
    return {
        "x": int(round(float(position.get("x", 0.0)) * scale)),
        "y": y,
        "z": int(round(float(position.get("z", 0.0)) * scale)),
    }


def _to_luanti_float(position: dict[str, Any], scale: float) -> dict[str, float]:
    return {
        "x": round(float(position.get("x", 0.0)) * scale, 3),
        "y": round(float(position.get("y", 0.0)) * scale + 1.0, 3),
        "z": round(float(position.get("z", 0.0)) * scale, 3),
    }


def _line_blocks(start: dict[str, int], end: dict[str, int]) -> list[dict[str, int]]:
    dx = end["x"] - start["x"]
    dz = end["z"] - start["z"]
    steps = max(abs(dx), abs(dz), 1)
    blocks = []
    seen: set[tuple[int, int, int]] = set()
    for step in range(steps + 1):
        ratio = step / steps
        pos = {
            "x": int(round(start["x"] + dx * ratio)),
            "y": start["y"],
            "z": int(round(start["z"] + dz * ratio)),
        }
        key = (pos["x"], pos["y"], pos["z"])
        if key not in seen:
            seen.add(key)
            blocks.append(pos)
    return blocks
