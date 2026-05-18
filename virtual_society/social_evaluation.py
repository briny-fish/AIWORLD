from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import pstdev

from .model import WorldState


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
