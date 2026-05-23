# ADR-0013: Local LLM calls are cacheable and replayable

## Status

Accepted

## Context

Generated cognition, reflection, and dialogue are now part of the alpha test
path. Live Codex CLI calls are useful for seeing whether agent identity and
memory can change behavior, but they introduce an experimental problem: a run
can be expensive, slow, and hard to reproduce exactly.

The project needs a way to separate two questions:

- What did a live LLM provider produce for a given prompt?
- What did the simulation do after receiving that exact provider output?

## Decision

Codex CLI providers can now use a disk-backed raw prompt/response cache. The
cache key includes schema version, provider, surface, model, reasoning effort,
and the full prompt. Each record stores the full prompt, response, prompt hash,
and metadata.

The CLI exposes three active modes:

- `read-write`: use a cached response when present, otherwise call Codex CLI and
  persist the raw response.
- `read-only`: require a cached response and fail fast on cache miss.
- `refresh`: ignore existing records and overwrite them with fresh live output.

`off` remains the default. The cache is wired into cognition, reflection, and
dialogue Codex CLI providers.

## Consequences

LLM experiments can now be run in two phases: live capture, then deterministic
replay. Replay still goes through the same JSON parser, policy checks, trace
recording, impact evaluation, and outcome evaluation as a live provider call.
The cache does not make LLM output authoritative world state; Simulation Core
continues to be the only state judge.

This gives the project a stronger experimental loop:

- capture a generated decision once,
- replay it repeatedly while changing evaluators or visualization,
- compare rule baselines against a fixed generated intent,
- keep prompt and response evidence for review.

The next iteration should add cache summaries to run reports so an observer can
see which generated surfaces were live calls and which were replayed.
