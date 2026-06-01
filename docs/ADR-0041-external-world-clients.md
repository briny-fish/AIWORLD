# ADR-0041: External World Clients, Not a New 3D Core

## Status

Accepted

## Context

The project goal is not to build a 3D engine. The goal is a long-running
virtual society where individuals have identity, memory, relationships,
conversation, and constrained action inside a persistent world.

The current prototype already has a deterministic Simulation Core, a local API,
2D/3D observer surfaces, agent dossiers, world object dossiers, and visible
LLM provider status. The product gap is that the society is still hard to read:
conversation, influence, memory, and social causality are not visible enough in
the live experience.

Existing work should be reused where it helps:

- Three.js/Babylon.js can support browser-native observer clients.
- Godot can support a richer 3D client without browser constraints.
- Luanti/Minetest can support a Minecraft-like voxel proof of concept.
- Minecraft agent projects such as Voyager and Mineflayer are useful research
  references, but should not become the authoritative world model.
- AI Town is a useful reference for social presence and chat UI, but should not
  replace the existing Simulation Core.

## Decision

Keep the Simulation Core authoritative and engine-agnostic.

The next phase will create a stable "world client protocol" that external
clients can read. External 3D or voxel clients may visualize the world and
submit bounded observer interventions, but they must not mutate world state
directly.

The implementation sequence is:

1. Make social life legible in the current browser observer.
2. Extract a stable client-facing world frame protocol.
3. Build a small Luanti/Godot-compatible adapter proof of concept.
4. Decide whether the main product client should remain web-first, move to
   Godot, or support both.

## Non-Goals

- Do not rewrite the Simulation Core inside a game engine.
- Do not turn the project into "AI plays Minecraft."
- Do not make 3D the next bottleneck before conversations, memories, and
  influence chains are visible.
- Do not let an external client bypass the existing intervention protocol.

## Consequences

This keeps the project's moat in the social simulation layer: identity,
memory, relationships, LLM-governed intent, historical scars, and evaluation.

3D engines become replaceable clients. If Luanti, Godot, Babylon.js, or another
runtime turns out to be the wrong fit, the core project does not need to be
rewritten.

The immediate product improvement still happens in the current live observer,
because that is the fastest place to expose dialogue, conversation history, and
social influence.

