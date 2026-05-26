# ADR-0027: Bounded API full-loop run

## Status

Accepted

## Context

ADR-0026 added API-backed reflection and dialogue providers. The next question
was whether all three generated surfaces can operate on the same social history
without breaking the deterministic simulation boundary:

- cognition chooses structured plans;
- dialogue creates grounded social memory;
- reflection interprets recent memory;
- later plans can show context deltas against the rule baseline.

This is the smallest meaningful "generated society loop" test. It is still
bounded by explicit budgets and deterministic fallback.

## Decision

Run a 30-day full-loop probe on `generative_alpha` with all three generated
surfaces enabled:

- `--cognition hybrid-openai`
- `--reflection hybrid-openai`
- `--dialogue hybrid-openai`

The probe keeps the scope narrow:

- cognition whitelist: Bo and Kira (`a2,a11`);
- generated cognition calls: 8;
- generated reflection calls: 2;
- generated dialogue calls: 2;
- counterfactual cognition gate: 3-day horizon;
- rule-baseline comparison enabled.

## Evidence

Configuration:

- model: `gpt-5.5`
- provider: OpenAI-compatible Dragon Code endpoint
- world preset: `generative_alpha`
- scenario: `observer-reconcile-vs-food-logistics`
- seed: 7
- duration: 30 days

Artifacts:

- `artifacts/run-openai-gpt55-full-loop-m23c.html`
- `artifacts/run-openai-gpt55-full-loop-m23c.json`
- `artifacts/cognition-trace-openai-gpt55-full-loop-m23c.json`
- `artifacts/reflection-trace-openai-gpt55-full-loop-m23c.json`
- `artifacts/dialogue-trace-openai-gpt55-full-loop-m23c.json`
- `artifacts/llm-cache-openai-gpt55-full-loop-m23c/`

Provider reliability:

- cognition: 8 attempts, 8 successes, 0 failures;
- reflection: 2 attempts, 2 successes, 0 failures;
- dialogue: 2 attempts, 2 successes, 0 failures.

Evaluation highlights:

- cognition accepted: 7 / 8 generated proposals;
- cognition divergence rate: 88%;
- counterfactual gate rejected 1 proposal;
- reflection memory grounding: 2 / 2;
- dialogue memory grounding: 2 / 2;
- generated chain found: dialogue day 1 -> Kira reflection day 7 -> later
  plan-context divergence.

Rule-baseline comparison:

- average need: `+0.034`;
- average trust: `+0.043`;
- institutional cohesion: `0`;
- crisis events: `-7`.

## Consequences

This is the first run where API-backed cognition, dialogue, and reflection all
participate in the same history and produce a measurable generated chain. It is
evidence that the architecture is moving toward the original goal: social
change can flow through memory and interpretation rather than only through a
rule score.

The run also shows the next problem clearly. The generated loop improved the
baseline but did not solve the scenario: the final state still had low wellbeing,
many relationship crises, and blocked routes. The next stage should therefore
improve observability and diagnosis, not just add more calls:

- surface generated chains prominently in the HTML observer;
- show why route blocks and relationship crises continue after generated repair
  attempts;
- run a second full-loop seed only after the observer makes the causal story
  readable.
