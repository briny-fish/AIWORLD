# ADR-0028: Story-first generated chain observer

## Status

Accepted

## Context

ADR-0027 proved that API-backed dialogue, reflection, and cognition can form a
measurable generated chain. The evidence was technically present in the HTML
report, but it was too easy to miss: generated chains appeared after several
trace tables, while the top of the report still emphasized aggregate metrics.

For the project goal, this is the wrong product shape. A user should quickly see
whether the society is developing history through memory and interpretation,
then inspect traces only when they need proof.

## Decision

Promote generated-chain evidence into the observer story layer:

- generated chains now produce a top-level story card;
- run JSON records now include `run_diagnosis`;
- HTML reports now render a `Run Diagnosis` section near the top.

`Run Diagnosis` is intentionally not another evaluation framework. It is a
readability layer over existing evidence:

- generated loop activity;
- remaining relationship pressure;
- remaining route pressure;
- rule-baseline delta;
- unresolved health findings.

## Evidence

The M23c full-loop artifact was regenerated from the committed read-only LLM
cache so no additional API calls were made.

Updated artifact:

- `artifacts/run-openai-gpt55-full-loop-m23c.html`
- `artifacts/run-openai-gpt55-full-loop-m23c.json`

The run now shows these top-level story cards:

- Outcome against rule baseline;
- Generated loop carried memory forward;
- Generated cognition changed behavior;
- Counterfactual gate filtered risk.

The run diagnosis now shows:

- Generated loop;
- Relationship pressure;
- Route pressure;
- Rule baseline delta;
- Health floor.

## Consequences

The observer can now communicate the project's current truth more honestly:

- there is a real generated loop;
- it improved the rule baseline;
- the world still has unresolved route and relationship bottlenecks.

This keeps the project aligned with the final goal. We are not hiding behind
LLM text quality; we are showing where generated agency affects the society and
where the world still resists it.
