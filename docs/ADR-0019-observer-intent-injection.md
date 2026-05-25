# ADR-0019: Observer intent injection starts as targeted broadcast

## Status

Accepted

## Context

The charter says users should eventually be able to enter the society as
participants. That full milestone includes natural-language intent parsing,
mapping user intent to executable plans, persistent user memory, relationships,
and identity. Doing all of that now would pull the project toward interface work
before the society has enough generated agency.

The smaller useful step is to let the observer influence agents through the
existing intervention boundary, while preserving the Simulation Core as the only
state authority.

## Decision

Broadcast interventions may now carry a structured `intent` and optional
`target_agent_ids`.

Supported intents are normalized to a small set:

- `repair_routes`
- `reconcile_relationships`
- `protect_food`
- `coordinate`

The intervention records a broadcast event and writes it into the target agents'
memory streams. Rule cognition can use the remembered intent as a plan bias, but
only if the individual agent has that broadcast in its own memory stream. Global
recent events do not apply targeted intent to non-target agents.

The intent still does not directly change routes, relationships, or resources.
It can nudge needs and later planning, and the Simulation Core decides whether
the resulting plan is valid and executable.

## Consequences

This is the first narrow version of user participation. It is enough to test
whether user influence becomes social memory and later behavior, without
building full roleplay identity yet.

The next step should expose this through the observer UI with explicit controls
for choosing intent and recipients. Full user-as-agent roleplay remains later,
after generated agents can reason more reliably over persistent history.
