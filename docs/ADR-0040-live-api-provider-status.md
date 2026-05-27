# ADR-0040: Live API Provider Status

## Status

Accepted

## Context

M39 proved that the DragonCode/OpenAI-compatible API path works in offline CLI
runs. That still left a product gap: the local browser observer is served by
`--serve`, and `--serve` previously always created a rule-only simulation.

This made API usage invisible in the experience the user actually sees. A
separate CLI artifact could prove API calls happened, but the live observer
could not show whether the current server was rule-only, cached, or backed by a
live LLM provider.

## Decision

Let the local API service accept the same generated providers as offline runs.

Changes:

- `SimulationService` accepts optional cognition, reflection, and dialogue
  providers;
- `run_server` accepts those providers and passes them into the stateful
  simulation;
- `python -m virtual_society.cli --serve` now builds providers from the normal
  `--cognition`, `--reflection`, `--dialogue`, `--openai-*`, and cache flags;
- `/provider-status` exposes provider mode, model, config, call stats, trace
  length, and cache mode;
- `/report/run.json` from the live service now includes provider traces and LLM
  cache summaries when present;
- the 2D and 3D observers fetch `/provider-status` and display provider mode in
  the metrics surface.

## Consequences

API use is now visible in the live product surface. To demonstrate a live API
observer run, start the server with explicit provider flags, for example:

```powershell
$env:OPENAI_API_KEY = "<set locally>"
$env:OPENAI_BASE_URL = "https://dragoncode.codes/v1"
python -m virtual_society.cli --serve --world-preset generative_alpha --seed 7 --port 8765 --cognition hybrid-openai --llm-agent-ids a1,a2,a11 --llm-every-days 2 --llm-max-calls 4 --reflection hybrid-openai --reflection-agent-ids a1,a11 --reflection-min-day 7 --reflection-max-calls 2 --dialogue hybrid-openai --dialogue-agent-ids a1,a11 --dialogue-max-calls 2 --openai-model gpt-5.5 --llm-cache-mode refresh --llm-cache-dir artifacts/llm-cache-live-openai-gpt55
```

The key remains a local environment variable. It is not stored in config,
reports, cache records, or git history.
