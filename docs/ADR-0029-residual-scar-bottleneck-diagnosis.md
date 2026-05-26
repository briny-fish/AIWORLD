# ADR-0029: Residual scar bottleneck diagnosis

## Status

Accepted

## Context

ADR-0027 showed that API-backed dialogue, reflection, and cognition can form a
generated loop. ADR-0028 made that loop visible near the top of the HTML
observer. The remaining problem is sharper now: the loop is real, but it does
not automatically resolve active historical scars.

The M23c full-loop run still ended with many relationship crises and blocked
routes. A generic count is not enough. The system needs to explain why those
scars remain:

- no direct social repair happened;
- social repair happened but trust stayed below the reconciliation threshold;
- trust is already above threshold but needs one more direct social contact;
- route repair is blocked by missing workshop materials;
- route repair is blocked by institutional cohesion;
- route repair is progressing but still has backlog.

## Decision

Add `scar_diagnosis.py` with `assess_scar_bottlenecks`.

The report now writes `scar_diagnosis` into run JSON and renders a
`Residual Scar Diagnosis` section in HTML. `Run Diagnosis` also uses the most
specific scar bottleneck as evidence instead of only counting remaining scars.

This is deliberately a diagnosis layer, not a new world rule. It does not make
repairs easier and it does not change simulation state. It tells the next agent
or observer what kind of intervention or generated decision would actually
matter.

## Evidence

The M23c full-loop run was regenerated from read-only LLM cache, with no new API
calls.

Updated artifact:

- `artifacts/run-openai-gpt55-full-loop-m23c.html`
- `artifacts/run-openai-gpt55-full-loop-m23c.json`

Residual scar diagnosis distribution:

- `no_direct_social_repair`: 21 relationship crises;
- `repair_below_threshold`: 6 relationship crises;
- `ready_but_unreconciled`: 5 relationship crises;
- `material_starved`: 9 blocked routes.

Top-level run diagnosis now identifies:

- relationship pressure: `no_direct_social_repair`;
- route pressure: `material_starved`.

## Consequences

The next generated loop experiment has a concrete target. More LLM calls are
not automatically useful unless they produce:

- direct social repair for specific crisis pairs;
- workshop material movement before route repair;
- repeated repair pressure until blocked routes reopen.

This keeps the project aligned with the original goal: the society should
evolve through world constraints, memory, and generated intent, while the
observer can understand why a social problem persists.
