# ADR-0033: Agent Dossiers

## Status

Accepted

## Context

The world dashboard makes the settlement legible, and the daily life journal
makes each agent's recent experience persistent. The next observer gap is
inspection: a user needs to select a person and see that person's life,
memories, and relationships together.

Full roleplay entry is still too large a milestone. A read-only dossier is the
right intermediate step because it raises product visibility without changing
simulation authority.

## Decision

Add an `Agent Dossiers` section to run HTML reports.

Each dossier is an expandable HTML `<details>` block for one agent. It contains:

- identity, role, location, current need, and trust;
- a recent `Life Timeline` built from `life_journal`;
- recent structured memory entries;
- the weakest relationship links and whether each is in crisis.

This is a report/observer feature only. It reads from the run record and does
not create or modify state.

## Evidence

Tests now assert that run HTML contains:

- `Agent Dossiers`;
- `Life Timeline`;
- `Daily Life` evidence in agent cards.

Validation command:

- `python -m unittest tests.test_reports`

## Consequences

This makes the current alpha closer to a virtual world viewer: the observer can
inspect individuals rather than only global metrics.

The next step is to make these dossiers live in the API/2D observer, then allow
bounded observer actions from the selected agent context.
