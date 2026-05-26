# ADR-0031: World Dashboard Alpha

## Status

Accepted

## Context

The project direction is shifting from a report-first settlement simulator
toward a virtual-world alpha. The simulation core and evaluation stack are
useful, but the first screen should no longer feel like only a metrics report.

The next viewer layer needs to make the society legible as a world:

- where people are;
- which routes are open or blocked;
- what the recent social story is;
- which agents are under pressure;
- which relationships are weak or scarred;
- what concrete observer actions can be taken next.

This must stay a presentation layer. It should not add hidden state changes or
grant LLM providers new authority over the world.

## Decision

Add a `World Dashboard` section near the top of run HTML reports.

The dashboard renders:

- an SVG settlement map with locations, routes, blocked routes, and agent
  positions;
- a concise social story panel based on the social chronicle;
- observer next moves from `observer_recommendations`;
- agent life cards with location, role, needs, trust, active plan, social
  pressure, and latest reflection or memory;
- a relationship web panel with active relationship scars and the weakest
  current ties.

Add `relationship_links` to the run record. This is derived from reciprocal
agent trust and active relationship crises. It is read-only report material and
does not change simulation behavior.

## Evidence

The M23c full-loop artifact was regenerated from read-only cache with no API
calls:

- cognition: 8/8 cache hits;
- reflection: 2/2 cache hits;
- dialogue: 2/2 cache hits.

Updated artifact:

- `artifacts/run-openai-gpt55-full-loop-m23c.html`
- `artifacts/run-openai-gpt55-full-loop-m23c.json`

Static verification confirms the HTML contains:

- `World Dashboard`;
- `Settlement Map`;
- `Agent life cards`;
- `Relationship Web`;
- `Observer Next Moves`.

Automated tests now assert the run record includes `relationship_links` and that
the HTML renders the world dashboard.

## Consequences

This is not the final virtual world. It is the first artifact where the
observer can start by reading a world state instead of scanning tables.

The next step should move from static readability to interaction:

- selecting an agent should foreground that agent's relationships and memory;
- observer recommendations should be directly schedulable from the live
  observer UI;
- the 3D observer should reuse the same story and relationship data instead of
  remaining a separate prototype.
