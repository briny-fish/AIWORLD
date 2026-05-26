# ADR-0035: Live Observer Alpha

## Status

Accepted

## Context

The project now has readable world reports, daily life journals, agent
dossiers, and a read-only agent dossier API. The next product gap is that the
live observer still behaves like an early metrics/debug panel.

To move toward a virtual world, the first live screen should show the current
settlement map, let the user select individuals, and expose that person's life
timeline and social pressure without requiring a generated report.

## Decision

Upgrade the 2D observer to a live observer alpha.

The observer now:

- fetches `/report/run.json` alongside `/state`, `/metrics`, and `/events`;
- renders a location and route map with blocked route styling and agent cards
  placed near their current locations;
- shows a `World Pulse` panel with social chronicle, scar counts, and observer
  recommendations;
- fetches `/agents/{id}` when a user selects an agent;
- renders selected agent identity, current plan, recent life journal, recent
  memories, and relationship pressure;
- adds `Step 30 Days` and `Reset Alpha`;
- supports selected-context actions: broadcast intent, mediate the selected
  agent's active relationship crisis, and add food at the selected location.

All write operations still go through existing Simulation Core interventions.
The observer remains a client over the API and does not directly mutate state.

## Evidence

The API test now asserts that `/observer` exposes:

- `Step 30 Days`;
- `World Pulse`;
- `Selected Agent`;
- `/agents/`.

Validation command:

- `python -m unittest tests.test_api`

Browser verification against `http://127.0.0.1:8765/observer` confirmed:

- 12 agent cards rendered;
- 8 location nodes rendered;
- 15 route lines rendered;
- selecting `a1` fetched the agent dossier;
- stepping one day updated the selected agent with a daily life entry;
- World Pulse did not duplicate day prefixes.

## Consequences

This is the first live product slice that uses the same world, dossier, and
observer recommendation data as the static reports. The next step should be
visual verification in the in-app browser through `http://127.0.0.1:<port>/observer`
and then lifting the same selected-agent panel into the 3D observer.
