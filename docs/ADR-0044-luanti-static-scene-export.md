# ADR-0044: Luanti Static Scene Export

## Status

Accepted

## Context

After `world-client-v1`, the project needs a proof that an existing embodied
runtime can consume the society without owning the Simulation Core. The user
specifically asked whether a Minecraft-like direction could reuse existing
work rather than building a 3D engine from scratch.

## Decision

Start M43 with a static Luanti/Minetest-style adapter.

Changes:

- `luanti_export.py` converts `world-client-v1` into `luanti-scene-v1`.
- The CLI can write the source frame via `--save-world-client-frame-json`.
- The CLI can write a Luanti scene via `--save-luanti-scene-json`.
- `adapters/luanti` contains a minimal Lua mod skeleton that reads
  `scene.json`, places location/route/organization nodes, spawns agent marker
  entities, and sends recent social events to chat.

## Consequences

This does not yet create a live multiplayer roleplay client. It proves the
mapping layer first: locations, blocked routes, agents, organizations, and
social log entries can leave the dashboard and appear in a voxel runtime.

The next version should replace the static `scene.json` file with live polling
of `/client/world-frame` through the Luanti HTTP API, while still routing all
world changes through the Python API intervention contract.
