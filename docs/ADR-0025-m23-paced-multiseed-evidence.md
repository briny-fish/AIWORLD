# ADR-0025: M23 paced API cognition needs multi-seed evidence

## Status

Accepted

## Context

ADR-0024 proved that OpenAI-compatible `gpt-5.5` cognition can run inside the
daily simulation loop with low latency and zero provider failures in the first
30-day trial. That result was not enough by itself: a single seed can make a
generated-cognition policy look better or worse than it really is.

M23 therefore needs a batch evidence layer that compares several run JSON
records and reports common signals:

- API success and failure rate;
- executed-plan divergence from the rule baseline;
- counterfactual gate acceptance and rejection;
- generated reason richness;
- final metric deltas against the deterministic rule baseline.

## Decision

Add a run-batch report path:

- `--run-batch-jsons` loads one or more run JSON artifacts.
- `--save-run-batch-json` writes an aggregate JSON record.
- `--save-run-batch-html` writes a human-readable HTML report.

The batch report is intentionally built from existing run JSON artifacts. It
does not rerun the simulation, and it does not need API access. This keeps M23
results replayable even if the API provider or model changes later.

## Evidence

The first paced M23 batch used:

- model: `gpt-5.5`
- provider: OpenAI-compatible Dragon Code endpoint
- world preset: `generative_alpha`
- scenario: `observer-reconcile-vs-food-logistics`
- seeds: 7, 8, 9
- duration: 30 days
- max generated cognition calls per run: 12
- max generated cognition calls per simulated day: 2
- counterfactual horizon: 3 days
- rule-baseline comparison enabled

Artifacts:

- `artifacts/batch-openai-gpt55-m23-paced-3seed.html`
- `artifacts/batch-openai-gpt55-m23-paced-3seed.json`
- `artifacts/run-openai-gpt55-m23-seed7-paced.html`
- `artifacts/run-openai-gpt55-m23-seed8-paced.html`
- `artifacts/run-openai-gpt55-m23-spread.html`
- `artifacts/llm-cache-openai-gpt55-m23-multiseed/`

Aggregate result:

- runs: 3
- generated cognition calls: 36
- provider failures: 0
- executed-plan divergence: 72.2%
- counterfactual acceptance: 81.2%
- average delta vs rule baseline:
  - average need: `+0.051`
  - average trust: `+0.057`
  - crisis events: `-7.667`

Per-seed result:

| Seed | Calls | Blocked | Divergence | Gate | Need | Trust | Crises |
|---|---:|---:|---:|---:|---:|---:|---:|
| 7 | 12 | 0 | 75% | 9/9 | +0.033 | +0.043 | -7 |
| 8 | 12 | 3 | 75% | 9/12 | +0.082 | +0.085 | -10 |
| 9 | 12 | 3 | 67% | 8/11 | +0.039 | +0.043 | -6 |

## Consequences

This is the first evidence that API-driven generated cognition is not merely
producing richer explanations; under daily pacing and counterfactual gating it
also improves short-run social outcomes across several seeds.

The conclusion is still bounded:

- three seeds are evidence, not proof;
- all runs used one scenario and one agent whitelist;
- reflection and dialogue are still rule-driven in this batch;
- generated cognition still often chooses `socialize`, so action-space pressure
  remains a live design issue.

The next M23 step is to increase breadth carefully:

- run a 5-seed paced batch;
- vary the scenario beyond observer reconciliation;
- add API-backed reflection or dialogue only after cognition remains stable;
- keep batch evidence visible in observer reports instead of burying it in raw
  JSON.
