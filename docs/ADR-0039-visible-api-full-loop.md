# ADR-0039: Visible API Full-loop Evidence

## Status

Accepted

## Context

Recent milestones focused on observability and participation contracts:

- `agent-dossier-v1` for individual continuity;
- `world-object-dossier-v1` for locations and organizations;
- 2D/3D observers consuming bounded affordance contracts.

Those milestones did not need LLM calls. The project should not spend API
budget just to exercise code paths, and API keys must never be written into
repository files. The next step was therefore to run a deliberately small,
auditable OpenAI-compatible probe that makes provider use visible through trace,
cache, and report artifacts.

## Decision

Run a bounded DragonCode/OpenAI-compatible full-loop probe with `gpt-5.5`.

The live API key was passed only through a process environment variable. It was
not stored in configuration, docs, cache records, reports, or git history.

Configuration:

- provider path: `hybrid-openai`;
- base URL: `https://dragoncode.codes/v1`;
- model: `gpt-5.5`;
- world preset: `generative_alpha`;
- scenario: `observer-reconcile-vs-food-logistics`;
- seed: `7`;
- duration: `8` days;
- cognition whitelist: `a1,a2,a11`;
- cognition budget: `4` calls;
- reflection budget: `2` calls;
- dialogue budget: `2` calls;
- cache mode: `refresh`;
- rule baseline comparison enabled.

## Evidence

Artifacts generated locally:

- `artifacts/run-openai-gpt55-m39-api-visibility.html`;
- `artifacts/run-openai-gpt55-m39-api-visibility.json`;
- `artifacts/cognition-trace-openai-gpt55-m39-api-visibility.json`;
- `artifacts/llm-cache-openai-gpt55-m39-api-visibility/`;
- `artifacts/run-openai-gpt55-m39-full-loop-visible.html`;
- `artifacts/run-openai-gpt55-m39-full-loop-visible.json`;
- `artifacts/cognition-trace-openai-gpt55-m39-full-loop-visible.json`;
- `artifacts/reflection-trace-openai-gpt55-m39-full-loop-visible.json`;
- `artifacts/dialogue-trace-openai-gpt55-m39-full-loop-visible.json`;
- `artifacts/llm-cache-openai-gpt55-m39-full-loop-visible/`.

Provider reliability in the full-loop probe:

- cognition: `4` attempts, `4` successes, `0` failures;
- reflection: `2` attempts, `2` successes, `0` failures;
- dialogue: `2` attempts, `2` successes, `0` failures.

Generated behavior evidence:

- cognition divergence rate: `75%`;
- counterfactual gate accepted `3 / 3` probed divergent proposals;
- Bo diverged from rule `repair` to generated `socialize` on day 2;
- generated dialogue was memory-grounded `2 / 2`;
- generated reflection was memory-grounded `2 / 2`;
- generated chains found: `2`.

Rule-baseline comparison at day 8:

- average need: `+0.035`;
- average trust: `+0.003`;
- institutional cohesion: `0`;
- crisis events: `-1`;
- food: `+0.88`;
- materials: `-0.3`;
- shelter: `-0.56`.

## Consequences

The API path is active and measurable. The project now has fresh evidence that
real generated cognition, dialogue, and reflection can operate on the same
social history while the Simulation Core remains the only state authority.

The result also clarifies why API use should be visible in reports instead of
hidden in logs. Some generated calls change behavior, while others keep the same
action but substantially enrich the reason and downstream social chain. The
next product step should surface API usage directly in the live observer:

- current provider mode;
- model and call budget;
- successful/generated call counts;
- latest generated chain;
- whether the current run is rule-only, cached, or live API-backed.
