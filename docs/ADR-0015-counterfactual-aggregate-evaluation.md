# ADR-0015: Counterfactual probes need aggregate evaluation

## Status

Accepted

## Context

ADR-0014 added a bounded counterfactual gate for individual generated cognition
decisions. That protects the simulation from accepting a locally worse proposal,
but a single probe is still only an anecdote. It cannot tell us whether a prompt,
agent profile, action pair, or provider is ready for a larger LLM budget.

The project goal is not to keep adding hand-authored rules. The next scale step
must be evidence-driven: generated cognition should earn more control only when
its decisions repeatedly survive deterministic probes and create traceable
world-state value.

## Decision

Every run now aggregates cognition-trace counterfactual records into a
`counterfactual_evaluation` report. The assessment records:

- total probes,
- accepted and rejected proposal counts,
- acceptance rate,
- average, worst, and best score deltas,
- the worst individual probe,
- buckets by agent,
- buckets by baseline/proposed action pair.

The CLI prints the summary after cognition trace output. Run JSON and HTML
reports include the same section when at least one counterfactual probe exists.

## Consequences

Counterfactual evaluation becomes a scaling gate for generated cognition. Before
expanding Codex CLI or API calls to more agents and more days, the project can
ask concrete questions:

- Which agents consistently benefit from generated cognition?
- Which action substitutions are dangerous?
- Does a prompt revision improve acceptance rate or only change prose?
- Are rejections clustered around one profile, resource condition, or social
  role?

This does not replace long-horizon outcome evaluation. It gives the project a
near-decision quality signal so larger LLM experiments are chosen from measured
behavior rather than intuition.
