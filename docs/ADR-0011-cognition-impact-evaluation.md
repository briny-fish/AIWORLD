# ADR-0011: Generated cognition must be evaluated at action level

## Status

Accepted

## Context

Generated dialogue and generated reflection can now enter memory and later plan
context, but that is still not the same as changing society behavior. The next
alpha question is whether generated cognition can safely influence the action
that the Simulation Core validates and executes.

Hybrid cognition already records the rule baseline, generated proposal, and
used plan. The missing piece was a report layer that connects that trace to
same-day execution evidence and to rule-baseline plan deltas.

## Decision

Runs can now include cognition impact evaluation. The evaluator records:

- accepted or blocked generated cognition calls
- rule baseline action, generated proposed action, and used action
- whether the used plan diverged from the rule baseline
- same-day execution evidence from the event log
- plan-history deltas against an optional deterministic rule baseline

Signals distinguish action divergence, plan-context divergence, policy-blocked
proposals, provider failures, and baseline-aligned accepted proposals.

The rest-override guard now treats recent exhaustion blocks in the agent's plan
history as valid evidence for rest. This aligns acceptance policy with the
prompt's own decision pressure field and prevents the guard from rejecting a
recovery plan simply because the exhaustion block was not the immediately
previous plan.

## Consequences

The project can now run small Codex CLI cognition experiments that answer a
sharper question: did generated cognition change an executable action, and what
did that do relative to the rule baseline?

This does not make LLM cognition the default. It makes action-level influence
observable and bounded, which is necessary before expanding call budgets,
agent counts, or provider use.
