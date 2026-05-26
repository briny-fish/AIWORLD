# ADR-0026: OpenAI-compatible reflection and dialogue providers

## Status

Accepted

## Context

ADR-0024 and ADR-0025 moved generated cognition from local Codex CLI debugging
into a paced OpenAI-compatible API path. That left an important gap: generated
plans could be API-driven, but weekly reflections and social dialogue still
needed either deterministic rules or local Codex CLI.

That gap matters because the project goal is not just better action selection.
The generated-agent layer needs identity, memory, dialogue, and reflection to
form a loop:

- dialogue enters memory;
- memory shapes reflection;
- reflection shapes later planning;
- later behavior creates new social history.

Keeping reflection and dialogue off the API path would keep the social
narrative layer weaker than the planning layer.

## Decision

Refactor the OpenAI-compatible Responses provider into a shared base and expose
three generated surfaces:

- `OpenAICognition`: structured `Plan` generation;
- `OpenAIReflection`: structured `ReflectionProposal` generation;
- `OpenAIDialogue`: structured `DialogueProposal` generation.

The CLI now accepts:

- `--reflection hybrid-openai`
- `--dialogue hybrid-openai`

These options reuse the same provider settings as cognition:

- `--openai-model`
- `--openai-base-url`
- `--openai-reasoning-effort`
- `--openai-timeout`
- `--llm-cache-dir`
- `--llm-cache-mode`

The API key remains outside the repository and must be supplied through
`OPENAI_API_KEY` or `VIRTUAL_SOCIETY_OPENAI_API_KEY`.

## Evidence

A first smoke run used:

- model: `gpt-5.5`
- provider: OpenAI-compatible Dragon Code endpoint
- world preset: `generative_alpha`
- scenario: `generative-alpha-storm`
- seed: 7
- duration: 14 days
- generated reflection budget: 1 call
- generated dialogue budget: 1 call

Artifacts:

- `artifacts/run-openai-gpt55-reflection-dialogue-m23b.html`
- `artifacts/run-openai-gpt55-reflection-dialogue-m23b.json`
- `artifacts/reflection-trace-openai-gpt55-m23b.json`
- `artifacts/dialogue-trace-openai-gpt55-m23b.json`
- `artifacts/llm-cache-openai-gpt55-reflection-dialogue-m23b/`

Result:

- reflection attempts: 1
- reflection successes: 1
- reflection failures: 0
- reflection memory grounding: 1 / 1
- dialogue attempts: 1
- dialogue successes: 1
- dialogue failures: 0
- dialogue memory grounding: 1 / 1

The generated dialogue on day 1 entered follow-through evaluation as
`memory_reflection_plan_echo`. The generated reflection on day 7 entered
follow-through evaluation as `plan_and_dialogue_echo`.

## Consequences

The project can now test a full generated loop with real API calls instead of
only generated plans. The next step is not to increase call volume blindly; it
is to run a bounded "full-loop" scenario where a small set of agents receive
API-backed dialogue, reflection, and cognition over the same 30-day history.

The key risks remain:

- token cost rises faster when all three surfaces are enabled;
- generated dialogue can pollute memory if it is vivid but poorly grounded;
- generated reflection can amplify a mistaken interpretation across later
  plans.

The existing memory citation requirements, trace files, cache, and follow-through
evaluations are therefore mandatory for API-backed reflection and dialogue runs.
