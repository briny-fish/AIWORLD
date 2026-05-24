# ADR-0017: Validate and narrate history before full roleplay

## Status

Accepted

## Context

The project goal is not just a stable simulation. It is a long-running virtual
society that users can observe, influence, and eventually enter, while social
change emerges from world constraints and agent reasoning instead of scripted
branches.

Persistent historical scars are now part of the Simulation Core, but that is
only a substrate. Before the user-as-character milestone becomes the product
focus, the project needs to prove two things:

- irreversible scars really persist, affect mechanics, and have repair paths;
- observers can read the resulting history as social change, not just as JSON
  counters or hidden state.

Existing social evaluators already measure shock traces, generated chains,
reflection follow-through, and cognition outcomes. The gap is not another
standalone evaluator. The gap is connecting those signals to the user-facing
history layer.

## Decision

The next sequence is:

1. Add a historical scar validation gate for relationship crises, organization
   fractures, blocked routes, and repair paths.
2. Add a social chronicle that turns recorded snapshots, scar events, and
   evaluation signals into a readable history panel in run reports.
3. Use Codex CLI next on real historical context, so generated cognition,
   reflection, and dialogue are tested against actual scars instead of routine
   resource pressure alone.
4. Narrow the first observer-participation milestone to intent injection through
   the existing broadcast/intervention protocol. Full user-as-agent roleplay is
   a later milestone because it also requires intent parsing, plan mapping,
   persistent user memory, and relationship state.

## Consequences

This keeps the project aimed at the charter instead of prematurely optimizing
for a roleplay interface. The society must first demonstrate durable history
and readable social consequences. Once that is visible, LLM-driven agents can be
judged on whether they reason over real history, and observer participation can
be added without turning into the center of the architecture too early.

M22-style "history readability evaluation" is not split out as a new framework.
The current evaluators remain authoritative; their outputs are surfaced through
the chronicle and reports.
