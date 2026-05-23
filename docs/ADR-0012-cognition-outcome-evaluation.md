# ADR-0012: Generated cognition requires outcome evaluation

## Status

Accepted

## Context

The project can now prove that generated cognition can change an executable
action. That is necessary, but not sufficient. A generated action can be more
human-like and still harm the society relative to the deterministic baseline.

The alpha therefore needs an outcome layer that compares post-decision metrics
against the same seed, scenario, and duration under rule-only cognition.

## Decision

Runs with a rule baseline can now include cognition outcome evaluation. For each
generated cognition impact, the evaluator records metric deltas at immediate,
short-window, and final horizons. It classifies outcomes as neutral, social
gain, social cost, resource gain, resource cost, or mixed tradeoffs.

The classification is deliberately simple and transparent. Social deltas use
average need, trust, and institutional cohesion. Resource deltas use food,
materials, and shelter. This is not a final welfare model; it is an alpha
instrument for seeing whether generated decisions are moving in the right
direction.

## Consequences

Generated cognition can now be judged by evidence rather than novelty:

- Did the generated plan change action?
- Was the action executed?
- Did short-term and final outcomes improve, worsen, or trade off against the
  rule baseline?

The next iteration should use these outcome labels to tune prompts and
acceptance policy. In particular, repeated `mixed_resource_gain_social_cost`
signals should force the project to distinguish useful recovery choices from
over-cautious rest choices.
