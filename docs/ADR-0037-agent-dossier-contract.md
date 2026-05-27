# ADR-0037: Agent Dossier Contract

## Status

Accepted

## Context

The project is moving from a settlement simulator toward a virtual world made of
continuous individuals. The 2D observer, 3D observer, run reports, API, and later
LLM or roleplay layers all need the same answer to a basic question:

> Who is this agent right now, what did they recently live through, what social
> pressure are they carrying, and how can the observer intervene without
> bypassing the Simulation Core?

Before this ADR, those fields were assembled in several places.

## Decision

Create `virtual_society.agent_dossiers` as the shared contract boundary for
agent-facing product data.

The contract version is `agent-dossier-v1`. It exposes:

- `build_agent_record(agent)` for stable report and UI agent summaries;
- `build_relationship_links(world)` for the shared relationship graph;
- `build_agent_dossier(world, agent_id)` for one selected individual;
- `build_agent_dossiers(world)` for an index of all individuals.

Each selected dossier now includes:

- identity and profile continuity;
- current plan;
- latest life episode;
- latest memory;
- latest reflection;
- pressure tags;
- weakest relationship and crisis count;
- recent actor events;
- relevant observer recommendations;
- bounded observer affordances with structured interventions.

`GET /agents/{id}` now returns this contract. `GET /agents` returns the full
dossier index. Reports now use the same `build_agent_record` and
`build_relationship_links` functions as the live API. The 2D and 3D observers
now render selected-agent intervention buttons from `observer_affordances`
instead of hardcoding those controls independently.

## Consequences

This does not make agents self-aware, and it does not add new behavioral rules.
It makes individual continuity a stable product surface. Future LLM reasoning,
story panels, 2D/3D UI sharing, and user-as-role participation should consume
this contract rather than reconstructing agent history ad hoc.

The next useful step is to extend `observer_affordances` beyond selected-agent
support into organization and location actions, so the user can intervene
through the same validated contract across every observable object.
