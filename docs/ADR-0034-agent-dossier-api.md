# ADR-0034: Agent Dossier API

## Status

Accepted

## Context

Agent dossiers are useful in static reports, but the project needs to become a
live virtual world. The observer and future 3D client need a direct way to fetch
one person's state without parsing the full run report.

This should stay read-only until the user-as-character model is designed.

## Decision

Add `SimulationService.agent_dossier(agent_id)` and `GET /agents/{id}`.

The endpoint returns:

- seed and current day;
- the agent record, including recent life journal entries;
- relationship links involving that agent;
- recent events authored by that agent;
- current observer recommendations from the run record.

The endpoint is a view over existing state. It does not schedule interventions
or mutate the simulation.

## Evidence

Tests cover both the service method and HTTP endpoint:

- `SimulationService.agent_dossier("a1")`;
- `GET /agents/a1`.

## Consequences

This gives future UI work a narrow contract for selecting an agent. The next
interaction step can use this endpoint to power a live side panel and then add
bounded observer actions from that selected context.
