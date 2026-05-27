# ADR-0036: 3D Agent Dossiers

## Status

Accepted

## Context

The 2D observer now uses the same world pulse and agent dossier data as the
static reports. The 3D observer still exposed only immediate needs, plan,
reputation, and organizations after selecting an agent.

For the final product direction, 3D must not remain a decorative visualization.
It has to reveal individual continuity: daily life, memory, relationships, and
bounded observer actions.

## Decision

Lift selected-agent dossiers into the 3D observer.

The 3D observer now:

- fetches `/agents/{id}` when a user selects an agent in the scene;
- keeps selected dossier data updated after stepping the simulation;
- renders the selected agent's recent life timeline;
- renders recent memory stream entries;
- renders relationship pressure chips;
- adds selected-context controls for broadcast intent, mediation, and food at
  the selected location;
- adds `30 Days` and `Reset Alpha` controls to match the live 2D observer.

All intervention controls continue to call `/step` with structured
interventions. The 3D observer does not directly mutate world state.

## Evidence

Static API tests assert `/observer3d` includes:

- `/agents/`;
- `Life Timeline`;
- `Food at Location`;
- `30 Days`.

Browser-level verification on `http://127.0.0.1:8765/observer3d` confirmed:

- Three.js renders a nonblank scene;
- clicking Ari selects the agent and loads `/agents/a1` dossier content;
- stepping one day refreshes the selected dossier with Day 1 life journal and
  memory entries;
- screenshot pixel sampling found varied nonblank colors in the rendered scene.

## Consequences

The 3D observer is now closer to a virtual-world surface rather than a visual
debug view. The next product step is to make selected-agent panels consistent
across 2D and 3D through shared data contracts or shared frontend helpers.
