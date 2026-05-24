# ADR-0016: The society needs persistent historical scars

## Status

Accepted

## Context

The simulation core, generated cognition traces, counterfactual gates, and
outcome evaluators can now show whether generated decisions changed behavior.
That is necessary but not sufficient for the project charter. A society that
always drifts back to a stable mean has pressure, but it does not have history.

The next product-level requirement is persistent consequence: weak ties,
institutional failure, and infrastructure strain must leave durable state that
later agents can observe, remember, repair, or fail to repair.

## Decision

The Simulation Core now records three kinds of historical scars:

- `relationship_crisis`: a pair whose reciprocal trust falls below the crisis
  threshold stops passively drifting back to the baseline. It can only be
  removed by direct social repair that raises trust above the repair threshold.
- `organization_fracture`: a low-cohesion organization with enough members can
  split. Alienated members form a splinter organization with its own membership,
  norms, home, cohesion, and future exchange behavior.
- `route_blocked`: a low-condition route under heavy strain becomes unavailable
  to pathfinding until common repair work spends materials and reopens it.

These mechanisms remain deterministic and are owned by the Simulation Core.
LLM providers can reason about these facts through memory, reflection, dialogue,
and cognition prompts, but they cannot directly create or remove the scars.

## Consequences

The project now has a stronger substrate for non-branching evolution. A storm,
scarcity period, or observer intervention can produce long-lived changes that
alter logistics, organizations, memories, and later plans without hand-authored
story branches.

Reports, history snapshots, and the observer expose active scars so users can
see what has changed. This also creates better material for later LLM scaling:
generated agents can be evaluated on whether they respond to real social and
spatial history, not just whether their prose differs from the rule baseline.

Default generative-alpha runs remain stable; historical scars are triggered by
actual low trust, low cohesion, and low-condition route strain rather than by
scripted narrative events.
