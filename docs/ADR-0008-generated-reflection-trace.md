# ADR-0008: Generated reflections are a bounded LLM experiment

## Status

Accepted

## Context

The generative alpha already has profiles, memory streams, deterministic weekly
reflections, and prompt-ready plan context. Plan-only LLM calls test whether a
model can choose an action inside the world constraints, but they do not test
whether identity and remembered experience become durable agent context.

Weekly reflection is the narrower next experiment. It happens less often than
daily planning, it can cite the memory stream directly, and later cognition can
consume the resulting reflection without giving the model authority over world
state.

## Decision

Periodic reflection now has the same provider boundary as cognition:

- `RuleBasedReflection` remains the deterministic long-run default and fallback.
- `HybridReflection` budgets generated reflection calls by agent, earliest day,
  call count, and failure count.
- `CodexCliReflection` can reuse the local Codex login for small experiments
  before API credentials are required.
- The reflection contract returns `summary`, `focus`, and `memory_refs`.
- Generated reflections must cite provided recent memory refs when memories are
  available.

Run JSON/HTML reports can include a reflection trace with the deterministic
baseline, generated proposal, accepted reflection, focus, cited memory refs, and
fallback errors. The CLI can save the same trace as a standalone JSON artifact.

The same reports can add a follow-through record for accepted generated
reflections. It scans a bounded post-reflection window for later plan and
dialogue evidence that overlaps reflection terms. When the CLI also runs the
same scenario against a rule-only baseline, the follow-through record includes
per-day plan-history deltas for the reflected agent.

## Consequences

This keeps reflection generation observable and evidence-bound. It does not
promote Codex CLI into the batch simulation backend, and it does not let a model
write world events or mutate resources directly.

The next behavior-quality question is no longer just whether a generated plan
diverges from the rule baseline. Reflection follow-through now answers the
first bounded version of that question for later plans and dialogue. A later
stage should extend the same evidence chain into organizational proposals and
longer-lived norm changes.
