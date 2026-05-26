# ADR-0032: Daily Life Journal

## Status

Accepted

## Context

The project goal is not a settlement metrics simulator. It is a virtual world
where individuals have persistent identity, memory, relationships, and enough
subjective continuity that an observer can understand them as lives unfolding
inside world constraints.

Before claiming any stronger agent subjectivity, the system needs a durable
per-agent record of daily experience. Event logs and plan history are useful,
but they are world-facing and action-facing. They do not answer the observer
question: what was this person's day like, and what pressure carried forward?

## Decision

Add `LifeEpisode` and `Agent.life_journal`.

Each simulation day now records one bounded life episode per agent:

- day, action, target, and final location;
- readable summary of the day;
- mood label derived from world state, not generated text;
- average need and trust before/after the day;
- pressure tags such as scarcity, fatigue, relationship crisis links, nearby
  blocked routes, or organization strain.

The daily life journal is generated after validated plans, actions, world
pressure, crises, and reflections have been applied. It is state evidence, not
an action authority. It cannot mutate resources, relationships, locations, or
organizations.

The journal is also added to:

- cognition context as `recent_life_journal`;
- reflection context as `recent_life_journal`;
- dialogue context for both participants;
- run records and the world dashboard agent cards.

The cognition prompt version becomes `cognition-plan-v4-daily-life`.

## Evidence

New tests assert that:

- every agent records one life episode per simulated day;
- life episodes include summary, pressure tags, and bounded need values;
- cognition, reflection, and dialogue contexts expose recent life journal
  entries;
- run HTML renders the daily life evidence in agent cards.

Targeted validation:

- `python -m unittest tests.test_simulation tests.test_llm_contract tests.test_reflection_contract tests.test_dialogue_contract tests.test_reports`
- `python -m compileall virtual_society tests`

## Consequences

This is still not "self-awareness". It is a required substrate for a virtual
world presentation: each agent now has a local continuity record that future LLM
providers can reason over without inventing facts.

The next step should turn this journal into interaction:

- clicking an agent should show the life journal timeline;
- observer actions should be visible inside later life episodes;
- LLM-generated reflections should be evaluated against the journal, not only
  against event memories.
