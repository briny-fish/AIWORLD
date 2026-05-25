# ADR-0021: Evaluate generated cognition under choice tension

## Status

Accepted

## Context

The previous Codex CLI probes showed that generated cognition can read
historical scars and observer intent, but the measured outcome often remains
neutral when the generated action matches the rule baseline. That creates an
evaluation gap: same-action outputs may still differ in whether they understand
the tradeoff behind the choice.

The project needs to distinguish:

- no tension: rule and generated cognition point at the same obvious action;
- action divergence: generated cognition chooses a different executable action;
- baseline alignment with tradeoff: generated cognition keeps the rule action
  but explicitly weighs competing historical and resource pressures;
- baseline alignment without tradeoff: generated cognition repeats the rule
  outcome without showing why competing pressures lost.

## Decision

Add `choice_tension_evaluation.py` and a report section named `Choice Tension
Evaluation`.

The evaluator links cognition trace rows with recent observer broadcasts that
the target agent actually remembered. It maps actions, observer intents, and
reason text into broad pressure groups such as food, logistics, repair, social,
materials, and recovery. A finding is emitted only when at least two competing
groups are present.

## Probe

Add `scenarios/observer-intent-vs-food-logistics.json`.

This scenario creates a route-repair intent for Bo while leaving food logistics
urgent enough that the deterministic rule baseline chooses `haul` on day 8.
Codex CLI was then run once for Bo with cached replay support:

- `artifacts/run-codex-choice-tension-m22.html`
- `artifacts/run-codex-choice-tension-m22.json`
- `artifacts/cognition-trace-codex-choice-tension-m22.json`
- `artifacts/llm-cache-codex-choice-tension-m22/`

## Result

Codex also chose `haul`, so there was no action-level divergence and no metric
delta against the rule baseline. The new evaluator classified the run as
`choice_tension_baseline_aligned_with_tradeoff`: Bo kept the logistics action,
but the generated reason mentioned food pressure, blocked routes, and recovery
constraints while carrying the remembered `repair_routes` observer intent.

## Consequences

This is a useful intermediate signal, not the final target. It shows that the
evaluation stack can now see meaningful tradeoff reasoning even before action
divergence appears. The next scenario should raise social or institutional
stakes enough that a generated provider has a credible reason to diverge at the
action level, then compare the social/resource cost over several post-decision
days.
