# ADR-0046: Product Goal Is Open World Agency, Not Full Causal Replay

## Status

Accepted

## Context

The project charter previously described the end product as a replayable
generative virtual society lab. That framing overemphasized causal replay. A
realistic society, even a simulated one, is chaotic and partially observable.
Trying to expose complete causal chains would push the project toward an
omniscient analysis tool instead of a living world.

The intended product is closer to a 3D open world populated by many NPCs with
their own thoughts, memories, goals, relationships, and local beliefs. The user
enters as a character, observes the world from inside or above it, and affects
the world through small or large interventions.

## Decision

Remove full causal replay as a product goal.

The new north star:

- a 3D open virtual world;
- many NPCs with their own memory, goals, preferences, and social relationships;
- the user can enter as a character;
- the user can observe, participate, and influence the world;
- influence can be small-scale or large-scale;
- society evolves through world constraints and generated NPC reasoning rather
  than scripted branches.

Existing trace, replay, and evaluation systems remain useful, but their role is
engineering support: debugging, regression testing, local explanation, and
measuring whether generated behavior affected visible society. They are not the
product's promise to reconstruct every cause.

## Consequences

Observer surfaces should prioritize situated legibility:

- what an NPC believes or remembers;
- what relationships and organizations matter to them;
- what they recently said or did;
- how the user is perceived by nearby NPCs;
- what visible changes the user's actions may have contributed to.

The project should still keep deterministic simulation safeguards where useful,
because they protect engineering quality. But product language should avoid
promising complete causality in a chaotic social world.

This shifts the next milestones toward embodied participation, NPC agency, and
3D/world-client experience rather than deeper global replay tooling.
