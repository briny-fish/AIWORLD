# ADR-0023: Batch Codex CLI cognition is a dry-run gate, not the production path

## Status

Accepted

## Context

The project needs to move from single generated cognition probes to repeated
LLM participation in the simulation loop. The existing infrastructure already
has hybrid cognition, cache/replay, counterfactual gates, outcome evaluation,
choice-tension evaluation, and now prompt versioning plus reason-richness
evaluation.

The next risk was no longer "can one LLM call work?" but "can the daily loop run
with several generated agents without losing observability or stability?"

## Decision

Run M23a as a local Codex CLI batch dry run before asking for an API key.

The dry run used:

- `prompt_version`: `cognition-plan-v3-social-pressure`
- world preset: `generative_alpha`
- scenario: `scenarios/observer-reconcile-vs-food-logistics.json`
- duration: 30 days
- allowed generated agents: Bo, Jules, Kira
- target budget: up to 6 generated cognition calls
- counterfactual gate: 2 days
- rule-baseline comparison enabled

Artifacts:

- `artifacts/run-codex-batch-m23a.html`
- `artifacts/run-codex-batch-m23a.json`
- `artifacts/cognition-trace-codex-batch-m23a.json`
- `artifacts/llm-cache-codex-batch-m23a/`

## Result

The simulation loop stayed stable for 30 days, but local CLI throughput was the
limiting factor.

The live read-write run attempted two calls:

- Bo succeeded.
- Kira timed out after the 300 second Codex CLI timeout.
- Because `--llm-max-failures` defaults to 1, the remaining planned calls fell
  back to the deterministic provider.

A replay was generated from the successful cache entry so the report uses the
current compact error handling and does not persist full prompt payloads inside
failure strings.

The successful Bo call is still important:

- rule baseline: `haul`
- generated plan: `socialize -> a1`
- reason: active relationship crisis with Ari, remembered observer intent, and
  route-dispute hardening risk
- counterfactual: accepted, score delta `+0.013`
- choice tension: `choice_tension_action_diverged`
- reason richness: `reason_richness_richer_with_behavior_delta`, generated
  score `7` versus baseline score `2`
- run-level final delta against the rule baseline: average need `+0.004`,
  average trust `0`, resources unchanged

## Consequences

M23a proved the batch evaluation/reporting path, but it also showed that local
Codex CLI is a poor production path for repeated in-loop cognition. It is still
useful for cached probes and small debugging runs, but true M23 requires an API
provider with lower per-call overhead and better timeout behavior.

The next step is M23b/M23c:

- keep reason richness in every generated cognition report;
- use the same scenario and evaluation stack with OpenAI API once an API key is
  available;
- compare local Codex CLI, OpenAI API, and the deterministic rule baseline on
  success rate, counterfactual rejection rate, action/target divergence, reason
  richness, and social/resource deltas.
