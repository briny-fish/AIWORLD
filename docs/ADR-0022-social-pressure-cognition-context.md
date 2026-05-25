# ADR-0022: Social pressure is explicit cognition context

## Status

Accepted

## Context

The first choice-tension probe showed that generated cognition could weigh
competing pressures, but it still followed the deterministic action. That was
not enough for the project goal: agents must eventually make different choices
because their identity, memory, and social history matter.

The previous cognition context exposed recent events and retrieved memories, but
it did not provide a compact structured view of the agent's active relationship
crises, weak ties, remembered observer intents, organization pressure, or
blocked routes. A model could infer some of that from event text, but the signal
was too indirect.

## Decision

Add social and institutional pressure fields to `decision_pressure` in the LLM
cognition context:

- `active_relationship_crises`
- `weakest_relationships`
- `organization_pressures`
- `remembered_observer_intents`
- `blocked_routes`

The prompt now treats those fields as real decision evidence. It also tells the
provider that `socialize` is valid when active crises or fracture risks justify
it, and that a social plan must use a concrete `target_id` from the structured
relationship evidence.

This does not change simulation settlement rules. The Simulation Core remains
the only state authority.

## Probe

Add `scenarios/observer-reconcile-vs-food-logistics.json`.

The scenario creates persistent relationship crises and route/depot logistics
pressure while keeping total food high enough that the conflict is not pure
starvation. The deterministic rule baseline for Kira on day 8 chooses `haul`;
Kira also remembers an observer intent to repair trust before council
cooperation hardens into factions.

Codex CLI was run once for Kira, then replayed through the counterfactual gate:

- `artifacts/run-codex-kira-reconcile-divergence-m23b.html`
- `artifacts/run-codex-kira-reconcile-divergence-m23b.json`
- `artifacts/cognition-trace-codex-kira-reconcile-divergence-m23b.json`
- `artifacts/llm-cache-codex-kira-reconcile-divergence-m23b/`
- `artifacts/run-codex-kira-reconcile-gated-m23c.html`
- `artifacts/run-codex-kira-reconcile-gated-m23c.json`
- `artifacts/cognition-trace-codex-kira-reconcile-gated-m23c.json`

## Result

Codex chose `socialize` while the rule baseline chose `haul`.

The accepted plan reason explicitly cited active relationship crises, remembered
observer intent, and Kira's role in preventing factions. The counterfactual gate
accepted the proposal: proposed score `-78.5431` versus baseline score
`-78.5501`, delta `+0.007`.

Run-level outcome remained small but measurable: average need `+0.001`, average
trust `+0.001`, food/materials/shelter unchanged, and crisis events `+1` against
the deterministic baseline over the 12-day comparison window.

## Consequences

This is the first action-level divergence that is both historically grounded and
accepted by the safety gate. It is not yet a broad social breakthrough: the
metric effect is small, and the scenario is still hand-authored. The next step
should repeat this pattern across several agents and seeds, then evaluate
whether generated social choices reduce active crises over longer windows
without degrading logistics.
