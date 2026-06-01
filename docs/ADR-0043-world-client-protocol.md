# ADR-0043: World Client Protocol

## Status

Accepted

## Context

The project is moving toward external embodied clients: Web 3D, Godot, Unity,
or Luanti/Minetest-style voxel worlds. Those clients need enough spatial and
social information to render the same society, but they must not become a
second simulation authority.

Before building a voxel or game-engine adapter, the API needs one stable,
versioned frame that describes the current world in render-ready terms.

## Decision

Add `world-client-v1`.

Changes:

- `world_client_protocol.py` builds a deterministic, JSON-only world frame.
- `GET /client/world-frame` returns locations, routes, agents, organizations,
  resources, metrics, recent social feed entries, provider status, visual hints,
  inspect URLs, and bounded affordances.
- The frame exposes a simple cartesian coordinate system with `y` as the up
  axis so Web 3D, Godot, Unity, or voxel adapters can map the same positions.
- Command affordances are expressed as HTTP method, endpoint, and payload, but
  all writes still go through `/step`, `/interventions`, or `/reset`.
- Route blockages, location condition, relationship pressure, organization
  fractures, active plans, recent memory, and latest reflection are included as
  observable client facts.

## Consequences

External clients can now render the living society without reading internal
`WorldState` objects or duplicating simulation logic.

The protocol is intentionally not a full game-engine schema. It is a bridge:
the Simulation Core remains authoritative, while clients are free to choose
their own geometry, animation, camera, HUD, and interaction style.

This makes the next milestone concrete: a Luanti/Minetest-style adapter can
consume `/client/world-frame`, render locations/routes/agents, and submit only
bounded interventions back to the Python service.
