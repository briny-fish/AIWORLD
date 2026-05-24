# ADR-0018: Probe Codex CLI against real historical scars

## Status

Accepted

## Context

After adding persistent historical scars and the readable social chronicle, the
next question is whether a local Codex CLI provider can reason over those facts
instead of only producing stylistic variation over routine resource pressure.

The test must keep the existing boundary intact: Codex CLI may propose
structured cognition, reflection, or dialogue outputs, but the Simulation Core
still validates plans, executes actions, records scars, and produces metrics.

## Decision

Run a small M19 probe on the `historical-scars-pressure` scenario:

- cognition: one Codex CLI plan call for Ari after route blockages and
  organization fractures are already visible;
- reflection: one Codex CLI reflection call for Ari on the same historical
  window;
- dialogue: one separate Codex CLI dialogue call with the first available
  social opportunity, because the pressure scenario has few social actions after
  day 7;
- all calls use the existing cache/replay mechanism and keep rule fallbacks,
  counterfactual gates, trace JSON, run HTML, and rule-baseline comparison.

## Results

The cognition probe diverged from the rule baseline. Ari's deterministic plan
was `haul`, while Codex proposed `repair` because repeated route blockages and
low route condition were becoming the practical bottleneck. The counterfactual
gate accepted it, but the measured outcome was neutral because repair was still
blocked by material shortages.

The reflection probe grounded itself in recent hunger crises and blocked
routes, then produced follow-through evidence in later plan context. This is a
useful signal: generated reflection can carry real historical pressure into
later planning language.

The dialogue probe produced one accepted dialogue, entered both agents'
memories, and showed memory, reflection, and plan echoes in the follow-through
window. It did not show baseline text deltas, so the value is visible but still
limited.

## Consequences

Codex CLI is now useful as a bounded local probe on real history. It should not
be scaled broadly yet. The next improvement should give generated decisions
more actionable room after scars: enough materials, repair targets, social
repair opportunities, and crisis-specific evaluation windows. Otherwise the
provider can choose the right strategic direction while the world still prevents
the action from changing outcomes.
