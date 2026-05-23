# ADR-0014: Generated cognition needs a counterfactual gate

## Status

Accepted

## Context

The project can now capture and replay raw Codex CLI prompt/response pairs.
That makes generated cognition reproducible, but reproducibility alone is not
enough. The earlier outcome evaluator works after the run. By then, a bad
generated plan may already have shaped later memory, reflections, and resource
flows.

The next step is to move part of the evaluation loop closer to the point of
decision, without letting the LLM become a world-state authority.

## Decision

Hybrid cognition can now run a short deterministic counterfactual probe before
accepting a divergent generated plan. For the same copied world snapshot, the
probe applies:

- the deterministic rule baseline plan,
- the generated proposal.

Each branch then advances for a short horizon under deterministic rule
cognition. The probe scores final metrics using social health, resource
adequacy, and crisis penalties. If the generated branch creates more crisis
events or trails the rule baseline by more than the configured threshold, hybrid
cognition keeps the rule baseline and records `baseline_after_counterfactual`.

The probe is deliberately bounded. It is not a perfect prediction of the future;
it is a fast safety and quality gate for obviously worse generated proposals.
The real world is never mutated during probing.

## Consequences

Generated cognition now has three layers of governance:

1. Structured JSON contract and Simulation Core validation.
2. Immediate acceptance policy for known risks such as unjustified rest
   overrides under shared pressure.
3. Short-horizon deterministic counterfactual probing for broader social and
   resource risk.

Reports and traces include the counterfactual recommendation, score delta, and
baseline/proposed scores. This gives prompt iteration a concrete target: improve
the generated plan until it survives deterministic probes, not just until it
looks plausible in prose.

The next iteration should aggregate these counterfactual records across seeds
and agents so the project can choose which profiles, situations, and prompts
are ready for larger LLM budgets.
