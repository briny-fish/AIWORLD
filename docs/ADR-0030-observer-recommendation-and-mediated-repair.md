# ADR-0030: Observer recommendations and mediated repair

## Status

Accepted

## Context

ADR-0029 made residual scars explainable. The next gap was participation:
diagnosis told the observer why relationship crises and route blocks remained,
but it did not produce concrete actions the observer could apply back into the
simulation.

The first recommendation pulse also showed a sharp split:

- workshop material recommendations helped blocked routes reopen;
- targeted relationship broadcasts created memory, but did not guarantee direct
  pair contact, so many relationship crises continued accumulating.

This means "broadcast intent" is useful as a low-force influence channel, but
it is not enough for pairs that are already near reconciliation and only need a
validated social repair event.

## Decision

Add `observer_recommendations.py`.

`build_run_record` now derives observer recommendations from
`scar_diagnosis`, stores them in run JSON, and renders them in the HTML report
as `Observer Intervention Suggestions`.

The CLI can also write:

- `--save-observer-recommendations-json`: full recommendation records;
- `--save-observer-intervention-file`: reusable intervention payloads.

`--intervention-file` is now repeatable, so a scenario file and a generated
recommendation file can be applied together in a follow-up run.

Add a bounded `mediation` intervention kind. It:

- requires exactly two known target agents;
- records a `mediation` event remembered by both agents;
- applies `world.rules.observer_mediation_trust_gain`;
- calls the existing reconciliation check instead of directly removing crisis
  state;
- keeps the Simulation Core as the only authority over durable world state.

The recommendation layer uses `mediation` for relationship crises that are
already above the repair threshold, or close enough that one bounded mediation
can plausibly clear the trust gap. Wider gaps still get targeted broadcast
intent.

## Evidence

M23c was regenerated from read-only cache with no API calls:

- cognition: 8 reads, 8 hits, 0 misses;
- reflection: 2 reads, 2 hits, 0 misses;
- dialogue: 2 reads, 2 hits, 0 misses.

Updated artifacts:

- `artifacts/run-openai-gpt55-full-loop-m23c.html`
- `artifacts/run-openai-gpt55-full-loop-m23c.json`
- `artifacts/observer-recommendations-openai-gpt55-full-loop-m23c.json`
- `artifacts/observer-interventions-openai-gpt55-full-loop-m23c.json`

The generated intervention file contains:

- one workshop material intervention for 9 blocked routes;
- six bounded mediation interventions;
- one lower-force relationship broadcast.

A 35-day recommendation pulse applied the scenario plus generated
interventions:

- LLM cache still hit 12/12 calls with no misses;
- 6 observer mediation events produced 6 reconciliation events;
- blocked routes fell from 9 at day 30 to 5 at day 35;
- active relationship crises rose from 32 at day 30 to 40 at day 35 because
  low wellbeing and safety pressure continued creating new crises.

The pulse is therefore a partial success: direct mediation repairs targeted
near-threshold pairs, and material suggestions unblock routes, but systemic
wellbeing pressure can still create more relationship damage than one pulse can
repair.

## Consequences

The project now has a real closed loop:

1. run the society;
2. diagnose residual scars;
3. generate concrete observer actions;
4. apply those actions in a follow-up run;
5. measure which scars changed.

This advances the original observe, participate, and influence goal without making the
observer omnipotent. The observer can schedule bounded social repair, but the
Simulation Core still validates targets, applies limited effects, records
memory, and decides whether reconciliation occurs.

The next work should focus on systemic pressure, not stronger one-off social
patches:

- recommend combined food, shelter, and route actions when wellbeing is below
  the health floor;
- surface the observer pulse outcome directly in the story layer;
- let future LLM cognition see observer mediation as historical social memory,
  while keeping the mediation rule out of prompt cache keys.
