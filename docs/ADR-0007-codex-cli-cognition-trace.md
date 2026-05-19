# ADR-0007: Local Codex CLI cognition tests require trace evidence

## Status

Accepted

## Context

The project is moving from mechanism coverage toward behavior-quality
evaluation. Local Codex CLI is useful before API credentials are required, but
it is too slow and variable to run as a large batch cognition backend.

The next LLM stage should therefore answer a narrow question: when Codex is
allowed to plan for a few agents at specific days, how does its plan differ
from the deterministic baseline, and does that difference help the society?

## Decision

Hybrid cognition records a trace for every attempted local Codex CLI call:

- day and agent
- deterministic rule baseline plan
- Codex proposed plan
- final used plan
- whether the plan diverged from the baseline
- error details when fallback is used

Run JSON/HTML reports can include this trace, and the CLI can save it as a
standalone JSON artifact. Local Codex CLI tests should stay small by default:
one to four calls, selected agents, selected days, and explicit call/failure
budgets.

## Consequences

This creates evidence for prompt and policy iteration before using an API key.
The current smoke result shows Codex can produce valid structured plans, but it
also tends to override productive rule plans with `rest` when agent energy is
near exhaustion. That may be correct human-like caution, or it may be excessive
conservatism. The next evaluation work should measure whether these overrides
improve recovery and long-run stability rather than treating any divergence as
automatically good.
