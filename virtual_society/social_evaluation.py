from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from statistics import pstdev

from .model import WorldState


SHOCK_EVENT_KINDS = {
    "disaster",
    "hunger_crisis",
    "safety_crisis",
    "institutional_crisis",
    "organization_fracture",
    "relationship_crisis",
    "route_blocked",
}

RESPONSE_TERMS_BY_KIND = {
    "disaster": {
        "damage",
        "damaged",
        "disaster",
        "gather",
        "gathering",
        "haul",
        "hauling",
        "materials",
        "repair",
        "shelter",
        "shock",
        "storm",
    },
    "hunger_crisis": {
        "distribution",
        "farm",
        "farming",
        "food",
        "haul",
        "hauling",
        "hunger",
        "rationing",
        "scarcity",
    },
    "safety_crisis": {
        "belonging",
        "crisis",
        "repair",
        "safety",
        "shelter",
        "socialize",
        "trust",
    },
    "institutional_crisis": {
        "belonging",
        "cohesion",
        "coordination",
        "institutional",
        "legitimacy",
        "organization",
        "socialize",
        "trust",
    },
    "organization_fracture": {
        "cohesion",
        "fracture",
        "institution",
        "organization",
        "repair",
        "splinter",
        "trust",
    },
    "relationship_crisis": {
        "crisis",
        "relationship",
        "repair",
        "socialize",
        "trust",
    },
    "route_blocked": {
        "blocked",
        "haul",
        "logistics",
        "materials",
        "repair",
        "route",
    },
}

STOP_TERMS = {
    "about",
    "after",
    "and",
    "day",
    "for",
    "from",
    "into",
    "society",
    "the",
    "their",
    "they",
    "this",
    "with",
}


@dataclass(frozen=True)
class SocialFinding:
    code: str
    severity: str
    day: int
    description: str
    value: float

    def as_dict(self) -> dict:
        return asdict(self)


def assess_social_dynamics(world: WorldState) -> list[SocialFinding]:
    population = max(world.population, 1)
    day = world.day
    findings: list[SocialFinding] = []

    memory_coverage = sum(1 for agent in world.agents if agent.memory_stream) / population
    reflection_coverage = sum(1 for agent in world.agents if agent.reflections) / population
    organization_coverage = sum(1 for agent in world.agents if agent.organization_ids) / population
    dialogue_count = sum(1 for event in world.event_log if event.kind == "dialogue")
    dialogue_per_agent = dialogue_count / population
    relationship_values = [
        trust
        for agent in world.agents
        for trust in agent.relationships.values()
    ]
    relationship_variance = pstdev(relationship_values) if len(relationship_values) > 1 else 0.0
    average_memory_depth = (
        sum(len(agent.memory_stream) for agent in world.agents) / population
    )

    if memory_coverage < 0.90:
        findings.append(
            SocialFinding(
                code="low_memory_coverage",
                severity="warning",
                day=day,
                description=f"Only {memory_coverage:.0%} of agents have structured memories.",
                value=round(memory_coverage, 3),
            )
        )

    if day >= world.rules.reflection_interval_days and reflection_coverage < 0.80:
        findings.append(
            SocialFinding(
                code="low_reflection_coverage",
                severity="warning",
                day=day,
                description=f"Only {reflection_coverage:.0%} of agents have reflections.",
                value=round(reflection_coverage, 3),
            )
        )

    if day >= 14 and dialogue_per_agent < 0.25:
        findings.append(
            SocialFinding(
                code="thin_dialogue",
                severity="warning",
                day=day,
                description=f"Dialogue density is low at {dialogue_per_agent:.2f} events per agent.",
                value=round(dialogue_per_agent, 3),
            )
        )

    if organization_coverage < 0.95:
        findings.append(
            SocialFinding(
                code="weak_organization_membership",
                severity="warning",
                day=day,
                description=f"Only {organization_coverage:.0%} of agents belong to organizations.",
                value=round(organization_coverage, 3),
            )
        )

    if day >= 90 and relationship_values:
        average_trust = sum(relationship_values) / len(relationship_values)
        if average_trust > 0.94 and relationship_variance < 0.05:
            findings.append(
                SocialFinding(
                    code="trust_saturation",
                    severity="info",
                    day=day,
                    description=(
                        "Trust is very high and low-variance; future versions need "
                        "more disagreement and norm pressure."
                    ),
                    value=round(average_trust, 3),
                )
            )

    if average_memory_depth < max(3.0, day * 0.20):
        findings.append(
            SocialFinding(
                code="shallow_memory_depth",
                severity="info",
                day=day,
                description=f"Average structured memory depth is {average_memory_depth:.1f}.",
                value=round(average_memory_depth, 3),
            )
        )

    shock_finding = _assess_shock_trace(world, population)
    if shock_finding is not None:
        findings.append(shock_finding)

    if not findings:
        findings.append(
            SocialFinding(
                code="social_loop_active",
                severity="info",
                day=day,
                description="Memory, reflection, dialogue, and organization participation are active.",
                value=1.0,
            )
        )

    return findings


def _assess_shock_trace(
    world: WorldState,
    population: int,
) -> SocialFinding | None:
    shock = next(
        (
            event
            for event in reversed(world.event_log)
            if event.kind in SHOCK_EVENT_KINDS
        ),
        None,
    )
    if shock is None:
        return None

    trace_window_days = 21
    if world.day - shock.day > trace_window_days:
        return None

    response_terms = RESPONSE_TERMS_BY_KIND.get(shock.kind, set())
    shock_terms = (_terms(shock.description) - STOP_TERMS) | response_terms
    memory_hits = 0
    reflection_hits = 0
    plan_hits = 0

    for agent in world.agents:
        if any(
            memory.day == shock.day
            and memory.kind == shock.kind
            and memory.text == shock.description
            for memory in agent.memory_stream
        ):
            memory_hits += 1

        if any(
            _has_term_overlap(reflection, shock_terms)
            for reflection in agent.reflections
            if _entry_day(reflection) >= shock.day
        ):
            reflection_hits += 1

        if any(
            _has_term_overlap(plan, shock_terms)
            for plan in agent.plan_history
            if shock.day < _entry_day(plan) <= shock.day + trace_window_days
        ):
            plan_hits += 1

    memory_coverage = memory_hits / population
    reflection_coverage = reflection_hits / population
    plan_coverage = plan_hits / population
    behavior_signal = max(reflection_coverage, plan_coverage)
    trace_score = (memory_coverage + behavior_signal) / 2

    if memory_coverage >= 0.60 and behavior_signal >= 0.20:
        return SocialFinding(
            code="shock_trace_active",
            severity="info",
            day=world.day,
            description=(
                f"Latest {shock.kind} on day {shock.day} is traceable: "
                f"memory {memory_coverage:.0%}, reflection {reflection_coverage:.0%}, "
                f"plan response {plan_coverage:.0%}."
            ),
            value=round(trace_score, 3),
        )

    return SocialFinding(
        code="shock_trace_weak",
        severity="warning",
        day=world.day,
        description=(
            f"Latest {shock.kind} on day {shock.day} is weakly traceable: "
            f"memory {memory_coverage:.0%}, reflection {reflection_coverage:.0%}, "
            f"plan response {plan_coverage:.0%}."
        ),
        value=round(trace_score, 3),
    )


def _entry_day(text: str) -> int:
    match = re.search(r"\bday\s+(\d+)\b", text.lower())
    if match is None:
        return 0
    return int(match.group(1))


def _has_term_overlap(text: str, terms: set[str]) -> bool:
    return bool(_terms(text) & terms)


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(term) > 1}
