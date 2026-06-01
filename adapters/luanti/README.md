# AIWORLD Luanti Adapter

This is the first external-client proof of concept. It treats Luanti
(formerly Minetest-style voxel clients) as an embodiment layer, not as the
authoritative simulation.

## Current Scope

- Python exports a static `luanti-scene-v1` package from `world-client-v1`.
- The scene contains location blocks, route blocks, organization markers,
  agent marker entities, and a small social log.
- The Lua mod skeleton loads `scene.json` from this folder and places the scene
  when a Luanti world starts.
- The adapter does not mutate simulation state directly. Future live commands
  must call `/step` or `/interventions`.

## Export

From the repository root:

```powershell
python -m virtual_society.cli --world-preset generative_alpha --seed 7 --days 8 --save-luanti-scene-json adapters/luanti/scene.json
```

Optional: save the source protocol frame too.

```powershell
python -m virtual_society.cli --world-preset generative_alpha --seed 7 --days 8 --save-world-client-frame-json artifacts/world-frame.json --save-luanti-scene-json adapters/luanti/scene.json
```

## Try In Luanti

1. Copy or symlink `adapters/luanti` into a Luanti mods directory as
   `aiworld_bridge`.
2. Enable the `aiworld_bridge` mod for a local world.
3. Start the world. The mod reads `scene.json` and places the static scene near
   origin.

The Lua mod uses common Luanti/Minetest mod APIs and keeps rendering simple on
purpose. If a game package lacks the expected default textures, replace the
`tiles` value in `init.lua`; the exported scene format stays the same.

References:

- Luanti nodes documentation: https://docs.luanti.org/for-players/nodes/
- Luanti registered entities API: https://api.luanti.org/registered-entities/

## Next Step

The live version should fetch `/client/world-frame` from the Python API using
the Luanti HTTP API, then refresh positions, blocked routes, and social text on
a timer. That comes after this static export proves the mapping is readable.
