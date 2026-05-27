# ADR-0038: World Object Dossiers

## Status

Accepted

## Context

Agent dossiers make individuals inspectable and actionable, but the intended
product is a virtual world, not only a list of people. Users also need to
understand and influence places and institutions: a damaged workshop, a blocked
route, a stressed council, or a household with inventory gaps.

The same rule still applies: observers can participate only through structured
interventions that the Simulation Core validates.

## Decision

Add `virtual_society.world_dossiers` as the shared contract boundary for
non-agent world objects.

The contract version is `world-object-dossier-v1`. It exposes:

- `build_location_dossier(world, location_id)`;
- `build_location_dossiers(world)`;
- `build_organization_dossier(world, organization_id)`;
- `build_organization_dossiers(world)`.

Location dossiers include:

- condition state;
- resource pressure;
- residents;
- connected route load and blockage state;
- recent object-linked events;
- bounded food/material/repair observer affordances.

Organization dossiers include:

- cohesion and fracture state;
- members;
- home location state;
- inventory gaps against organization targets;
- recent object-linked events;
- bounded coordination/stabilization observer affordances.

The local API now exposes:

- `GET /locations`;
- `GET /locations/{id}`;
- `GET /organizations`;
- `GET /organizations/{id}`.

## Consequences

Observer participation is no longer only agent-centric. The next UI step is to
make map locations and organization rows clickable in the observer, using these
object dossiers exactly as agent selection already uses `agent-dossier-v1`.

This still does not allow direct state edits. All affordances remain structured
interventions routed through `/step`.
