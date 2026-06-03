# ADR-0045: 3D Observer as World Frame Client

## Status

Accepted

## Context

`world-client-v1` was added so external renderers could visualize the society
without reading internal `WorldState` details. The existing Three.js observer
still used `/state`, `/metrics`, `/events`, and `/provider-status`, which meant
the built-in 3D client was not exercising the same boundary intended for
Luanti, Godot, Unity, or other external clients.

## Decision

Make `/observer3d` consume `GET /client/world-frame`.

Changes:

- The 3D observer now reads one frame from `/client/world-frame`.
- Locations, routes, agents, organizations, resources, provider status, and
  social feed entries come from `world-client-v1`.
- Route blockage rendering uses the protocol route state instead of client-side
  reconstruction.
- Agent scene placement uses protocol positions. Selected-agent details still
  fetch `/agents/{id}` on demand for deeper dossier information.
- The bottom-left panel now shows the protocol social feed rather than raw
  event rows.

## Consequences

The browser 3D observer is now the first built-in external-client reference
implementation. Future Luanti or Godot clients can follow the same read/write
boundary: read `/client/world-frame`, inspect deeper dossiers as needed, and
submit changes only through structured interventions.

This does not decide the final UI direction. It reduces risk by proving that a
world client can render the society through the same protocol that external
clients will use.
