# Next Phase Implementation Plan

This plan starts after ADR-0040. The purpose is to move from a rule-readable
settlement prototype toward a virtual society whose individuals can be observed
through conversation, memory, influence, and spatial presence.

## North Star

The final product should feel like a 3D open virtual world with many NPCs who
have their own thoughts, memories, relationships, and goals. It should not feel
like a dashboard of settlement rules or an omniscient causal replay system. The
user should be able to answer:

- Who talked to whom?
- What did they say?
- What did they remember?
- What local changes did my presence or actions seem to influence?
- Which world objects or relationships carry lasting history?
- How do nearby NPCs perceive me as a character in the world?
- Can an external 3D or voxel client show the same society without owning the
  simulation state?

## M41: Social Legibility UI

Goal: make the current browser observer show interpersonal life directly.

Scope:

- Add a live social feed for dialogue, relationship pressure, observer intent,
  reflection, organization, crisis, and reconciliation events.
- Add selected-agent conversation history to the dossier panel.
- Add an influence-chain panel that links dialogue or observer intent to memory,
  reflection, later plan context, and resulting actions when evidence exists.
- Mark whether social text came from rule fallback, cached LLM, or live LLM.
- Keep every state-changing action routed through `/step` or `/interventions`.

Primary code areas:

- `virtual_society/social_timeline.py` for shared feed extraction.
- `virtual_society/agent_dossiers.py` for conversation history and influence
  evidence attached to selected individuals.
- `virtual_society/api.py` for new read-only endpoints if needed.
- `virtual_society/observer.py` first; `observer3d.py` second.

Candidate endpoints:

- `GET /social-feed?limit=50`
- `GET /agents/{id}/social-history?limit=20`
- Optional: include summarized social history inside `GET /agents/{id}`.

Acceptance:

- A 30-day run has a readable feed of conversations and social consequences.
- Selecting Ari, Bo, or another agent shows recent conversations involving that
  agent.
- If a generated dialogue later appears in memory/reflection/plan context, the
  UI shows the chain without requiring the user to inspect raw JSON.
- Tests verify the feed builder, agent social history, API route, and observer
  page text.

## M42: World Client Protocol v1

Status: implemented as ADR-0043, with the built-in 3D observer migrated to the
same protocol in ADR-0045.

Goal: define the stable read contract that any 3D, voxel, or web client can
consume.

Scope:

- Add a versioned world-frame builder.
- Expose locations, routes, agents, organizations, recent social events,
  current plans, visual hints, and bounded affordances in one read-optimized
  payload.
- Keep simulation internals private.
- Keep commands separate from the frame. Clients read `/client/world-frame` and
  still submit only structured interventions.

Primary code areas:

- `virtual_society/world_client_protocol.py`
- `virtual_society/api.py`
- `tests/test_world_client_protocol.py`

Candidate endpoint:

- `GET /client/world-frame`

Frame shape:

```json
{
  "kind": "world_client_frame",
  "version": "world-client-v1",
  "day": 12,
  "seed": 7,
  "provider": {"live_llm_enabled": true, "models": ["gpt-5.5"]},
  "locations": [],
  "routes": [],
  "agents": [],
  "organizations": [],
  "social_feed": [],
  "affordances": []
}
```

Acceptance:

- The frame is deterministic for a fixed world state.
- The frame contains enough spatial and social data to render a simple 3D or
  voxel scene without reading `/state`.
- Tests ensure no direct mutable world objects leak into the payload.
- The existing 2D observer can optionally start consuming this frame for map
  data.

## M43: External Client Proof of Concept

Status: started as ADR-0044 with a static Luanti scene export and mod skeleton.

Goal: prove that an existing world runtime can visualize our society without
owning the social simulation.

Preferred first target: Luanti/Minetest-style voxel client.

Why:

- It is closer to the Minecraft-like direction the user asked about.
- It can visualize locations, route blockages, resources, and simple agent
  presence with relatively low art cost.
- It keeps embodiment concrete while avoiding a full custom engine.

Scope:

- Add `adapters/luanti/README.md`.
- Add a generated or hand-written minimal Luanti mod skeleton.
- Render 5-12 locations as blocks/structures.
- Render routes as paths, blocked routes as visible barriers.
- Render agents as simple entities or markers with names.
- Show recent dialogue in chat or a HUD-like text panel if the runtime permits.
- Submit only bounded interventions back to the Python API.

Fallback:

- If Luanti setup is too heavy on the local machine, build a static export
  first: generate a Lua/JSON scene package from `/client/world-frame`.

Acceptance:

- A user can start the Python simulation service, open the voxel client or
  generated scene, and recognize the same agents, locations, route state, and
  recent social events.
- The adapter cannot edit authoritative state except through interventions.
- The POC teaches whether voxel embodiment helps or distracts from social
  legibility.

## M44: Godot/Web Client Decision Gate

Goal: choose the durable client direction after one voxel POC and one richer UI
iteration.

Decision criteria:

- Does the client make relationships and conversations easier to understand?
- Can it show memory, influence, and social history without becoming cluttered?
- Can it reconnect to the Simulation Core without corrupting state?
- Can development continue quickly enough for long-term iteration?
- Does it support future roleplay entry without rebuilding the whole product?

Possible outcomes:

- Web-first: keep Three.js/Babylon.js and improve the browser observer.
- Godot-first: build a richer 3D desktop client against the protocol.
- Voxel-sidecar: keep Luanti as an experimental embodiment lab, not the main UI.
- Hybrid: use browser UI for social reasoning and Godot/Luanti for embodied
  world viewing.

## Immediate Development Order

1. Implement M41 social feed and selected-agent conversation history.
2. Verify it with both rule fallback and a small live/cached LLM run.
3. Implement M42 world client frame.
4. Refactor the existing 3D observer to consume the frame where practical.
5. Build the M43 Luanti adapter skeleton and scene export.
6. Run the M44 decision gate based on actual usability, not preference.
