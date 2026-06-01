# ADR-0042: Social Legibility UI

## Status

Accepted

## Context

The live observer could show metrics, agent dossiers, locations, organizations,
historical scars, and provider status. It still did not make interpersonal
life readable enough. Dialogue existed in events and memories, but users had to
inspect raw JSON to understand who talked, what was remembered, and whether a
conversation later affected reflection or planning.

M41 makes social causality a product surface before moving deeper into external
3D or voxel clients.

## Decision

Add a shared social timeline contract.

Changes:

- `social_timeline.py` builds `social-timeline-v1` payloads from events,
  dialogue traces, memory streams, reflections, plan history, and generated
  chain evaluations.
- `GET /social-feed?limit=50` returns a readable live social feed.
- `GET /agents/{id}/social-history?limit=20` returns selected-agent social
  history and influence chains.
- Agent dossiers now include `social_history` and `influence_chains`.
- Run records include `social_feed` and `influence_chains`.
- The 2D observer shows a global Social Feed and selected-agent Conversation
  History plus Influence Chain sections.

## Consequences

Users can now see dialogue, observer intent, relationship crises,
reconciliation, reflection, and organization pressure as social events rather
than raw event rows.

The observer still does not grant clients direct state mutation. All influence
continues to flow through `/step` or `/interventions`.

This gives future 3D, Godot, or Luanti clients a clearer social contract to
visualize. They can show "what happened socially" without reverse-engineering
the simulation internals.

