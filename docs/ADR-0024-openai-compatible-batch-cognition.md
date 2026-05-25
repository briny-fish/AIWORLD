# ADR-0024: OpenAI-compatible batch cognition with daily pacing

## Status

Accepted

## Context

ADR-0023 showed that local Codex CLI is useful as a dry-run gate but not as the
production path for repeated in-loop cognition. The next milestone needs real
API throughput, replayable prompt/response cache records, and enough pacing that
LLM participation does not hit many agents in the same simulated day.

The first OpenAI-compatible target is Dragon Code, verified through:

- base URL: `https://dragoncode.codes/v1`
- Responses endpoint: `https://dragoncode.codes/v1/responses`
- model: `gpt-5.5`

No API key is stored in the repository. The CLI receives it through
`OPENAI_API_KEY` or `VIRTUAL_SOCIETY_OPENAI_API_KEY`.

## Decision

Extend `OpenAICognition` from a hard-coded OpenAI Responses endpoint into an
OpenAI-compatible provider:

- `OPENAI_BASE_URL` / `VIRTUAL_SOCIETY_OPENAI_BASE_URL` /
  `--openai-base-url` can point to either a `/v1` base or a full
  `/v1/responses` endpoint.
- `--openai-reasoning-effort` can be passed through to the Responses API.
- generated cognition can use `LLMCallCache` with provider
  `openai-compatible`.
- `HybridCognitionConfig.max_calls_per_day` paces generated cognition across
  simulated days instead of spending the whole budget in one burst.

## Runs

Two M23 runs were generated on the same seed, scenario, world preset, model,
agent whitelist, and total call budget.

### Burst run

Artifacts:

- `artifacts/run-openai-gpt55-m23.html`
- `artifacts/run-openai-gpt55-m23.json`
- `artifacts/cognition-trace-openai-gpt55-m23.json`
- `artifacts/llm-cache-openai-gpt55-m23/`

Configuration highlights:

- days: 30
- model: `gpt-5.5`
- max generated cognition calls: 12
- daily cap: none
- counterfactual horizon: 2 days

Result:

- API reliability: 12 successes / 12 attempts.
- Counterfactual gate: accepted 8 / 9 divergent proposals.
- Behavior divergence: 67%.
- Final delta against rule baseline: average need `-0.028`, trust `+0.004`,
  shelter `-0.53`, crisis events `+1`.

This run proved throughput, but it concentrated generated cognition on days 6
and 9. The social reasons were richer, but the run-level outcome paid a short
term welfare cost.

### Paced run

Artifacts:

- `artifacts/run-openai-gpt55-m23-spread.html`
- `artifacts/run-openai-gpt55-m23-spread.json`
- `artifacts/cognition-trace-openai-gpt55-m23-spread.json`

Configuration highlights:

- days: 30
- model: `gpt-5.5`
- max generated cognition calls: 12
- daily cap: 2 calls
- counterfactual horizon: 3 days

Result:

- API reliability: 12 successes / 12 attempts.
- Counterfactual gate: accepted 8 / 11 divergent proposals, rejected 3.
- Behavior divergence: 67%.
- Final delta against rule baseline: average need `+0.039`, trust `+0.043`,
  shelter `0`, crisis events `-6`.

The daily cap changed M23 from "LLM burst test" into a more plausible
simulation-loop integration. Generated cognition still changed behavior, but
the run-level result became socially positive instead of paying a welfare cost.

## Consequences

OpenAI-compatible API cognition is now the preferred path for M23 and later LLM
experiments. Local Codex CLI remains a debug provider.

The next work should not add more evaluation layers. The evaluation harness is
already catching useful differences. The next work should:

- keep daily pacing enabled by default for batch experiments;
- compare several seeds before treating one positive run as stable evidence;
- expose the paced M23 result in the story/observer layer, not only JSON;
- start moving the same API provider pattern into reflection and dialogue once
  cognition behavior remains stable over multi-seed runs.
