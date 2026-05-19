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

The CLI can also run a deterministic rule-only baseline for the same seed,
world preset, duration, and interventions. Reports then include the final
metric deltas between the LLM-influenced run and the rule baseline. This keeps
LLM evaluation tied to observable social outcomes rather than treating plan
divergence as success by itself.

## Consequences

This creates evidence for prompt and policy iteration before using an API key.
The current smoke result shows Codex can produce valid structured plans, but it
also tends to override productive rule plans with `rest` when agent energy is
near exhaustion. That may be correct human-like caution, or it may be excessive
conservatism. The next evaluation work should measure whether these overrides
improve recovery and long-run stability rather than treating any divergence as
automatically good.

The first baseline-compared smoke run used one local Codex CLI call in the
`generative_alpha` storm scenario. Codex changed Ari's day 21 rule baseline
from `farm` to `rest`. The run stayed stable and maintained `shock_trace_active`,
but ended slightly below the rule baseline on average need (-0.004) and trust
(-0.002), with more food (+0.91) and less shelter (-0.58). That is not enough
to reject Codex-driven cognition, but it says the next prompt iteration should
ask the model to weigh individual recovery against shared production pressure
more explicitly.

The next iteration made the prompt baseline-aware and added an acceptance
policy in hybrid cognition. Codex still proposed `rest`, but the policy rejected
that override because shared resource pressure was active and the agent was not
at the exhaustion threshold or just blocked by exhaustion. The candidate plan
remained visible in trace, while the used plan returned to the rule baseline.
This restored final metric parity with the rule baseline. The important shift
is architectural: LLM output is now treated as a governed proposal, not as an
automatic replacement for deterministic cognition.
