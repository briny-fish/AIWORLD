# ADR-0010: Generated chain evaluation tracks cross-module causality

## Status

Accepted

## Context

Generated dialogue, generated reflection, and generated planning are useful only
if information can move through the agent loop instead of staying as isolated
LLM outputs. A single accepted dialogue trace proves that the provider returned
valid JSON. It does not prove that the dialogue entered memory, shaped a later
reflection, or changed later planning context.

## Decision

Runs can now include generated chain evaluation. The evaluator links:

- accepted generated dialogue
- accepted generated reflection by one of the dialogue participants
- participant memory evidence from the generated dialogue
- later plan evidence after the generated reflection
- optional rule-baseline plan deltas for the reflecting agent

The chain signal distinguishes action divergence from plan-context divergence
and ordinary text echoes. This keeps the evaluation honest: repeated terms are
evidence of information flow, not proof that world behavior changed.

## Consequences

This creates a bounded test for the current alpha question: can generated social
content survive through memory and reflection into later plans while the
Simulation Core remains the only state authority?

The next iteration should use the chain output to tune prompts and acceptance
policies, then run small paired experiments before expanding to more agents or
larger worlds.
