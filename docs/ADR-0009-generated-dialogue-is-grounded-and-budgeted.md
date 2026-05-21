# ADR-0009: Generated dialogue is grounded and budgeted

## Status

Accepted

## Context

Social dialogue is one of the highest-value LLM surfaces in the alpha. Dialogue
becomes memory for both participants, feeds later reflection context, and makes
an observer able to inspect how agents interpret shocks and coordination.

The deterministic dialogue template already injects salient events, profiles,
trust, and shared organizations. That is a useful baseline, but it cannot test
whether model-generated dialogue can carry richer agent-specific information.

## Decision

Social dialogue now has a provider boundary:

- `RuleBasedDialogue` preserves the deterministic template baseline.
- `HybridDialogue` limits generated dialogue by speaker allowlist, earliest day,
  call count, and failure count.
- `CodexCliDialogue` reuses the local Codex login for small pre-API experiments.
- The dialogue contract returns `text`, `focus`, and `memory_refs`.
- Generated dialogue must cite provided recent memories when memory evidence is
  available.

The Simulation Core still decides whether a social action occurred, who the
partner is, how trust and needs change, and which memories are recorded.
Generated dialogue only proposes the dialogue event text that replaces the
deterministic baseline when accepted.

Run JSON/HTML reports can include a dialogue trace with the deterministic
baseline, generated proposal, used dialogue, focus, cited memory refs, and
fallback errors. The CLI can save the same trace as a standalone JSON artifact.

## Consequences

The alpha can now test a richer social-information loop without pushing LLM
authority into state settlement. Local Codex dialogue experiments should remain
small until the trace shows that generated dialogue improves later memory and
reflection quality over the event-aware template baseline.
