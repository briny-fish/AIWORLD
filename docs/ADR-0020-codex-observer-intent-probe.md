# ADR-0020: Probe Codex CLI on observer intent follow-through

## Status

Accepted

## Context

Observer intent injection now lets a user send a bounded social intent into the
simulation without granting the user direct state-write authority. The next
question is whether local Codex CLI cognition can reason over that intervention
as part of agent history, rather than only reacting to resource pressure.

The first M21 probe attempted a day 7 Ari cognition call after the observer
asked Ari, Gale, and Jules to reopen blocked routes. It timed out at 180
seconds. The failure exposed a context-budget issue: the Codex CLI prompt still
included full simulation rules and verbose retrieved-memory records.

## Decision

Codex CLI cognition now uses a compact cognition context by default:

- keep the structured plan contract, baseline plan, decision pressure,
  selected rule thresholds, locations, organizations, memories, and recent
  events;
- remove the full rule table from the prompt;
- trim retrieved memories to the fields needed for grounded reasoning;
- keep the full Simulation Core state unchanged and authoritative.

The M21 probe was rerun at day 8, after Ari had recovered from the day 7
exhaustion block. The run used one local Codex CLI cognition call, rule fallback
protection, cache capture, rule-baseline comparison, and the observer-intent
scenario.

Artifacts:

- `artifacts/run-codex-observer-intent-m21.html`
- `artifacts/run-codex-observer-intent-m21.json`
- `artifacts/cognition-trace-codex-observer-intent-m21.json`
- `artifacts/llm-cache-codex-observer-intent-m21/`

## Results

The compact prompt reduced a representative cognition prompt from about 21K
characters to about 13.7K characters. The rerun completed successfully in about
120 seconds.

Codex proposed `repair` for Ari on day 8. The deterministic baseline was also
`repair`, so there was no action divergence and no measurable outcome delta.
However, the generated reason was grounded in the actual history: route-block
memories, recent common repair work, observer-intent follow-through, energy
pressure, and the rest policy. The cognition impact evaluator recorded this as
`cognition_plan_context_diverged`: same action, different causal explanation.

## Consequences

This is not yet evidence that generated cognition can outperform the rule
baseline. It is evidence that local Codex CLI can now run against observer
intent history without timing out, and that the generated explanation can carry
more historical context than the rule reason.

The next useful LLM probe should create a real choice conflict, for example
observer intent versus food pressure, role values versus organization fracture,
or repair versus reconciliation. Without a scenario that creates action-level
tension, LLM value will mostly appear as richer reasons instead of changed
social outcomes.
