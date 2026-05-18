from __future__ import annotations

from dataclasses import asdict, dataclass

from .model import Metrics


@dataclass(frozen=True)
class HealthFinding:
    code: str
    severity: str
    day: int
    description: str


@dataclass(frozen=True)
class RunReport:
    seed: int
    days: int
    final_metrics: Metrics
    findings: list[HealthFinding]

    def as_dict(self) -> dict:
        return {
            "seed": self.seed,
            "days": self.days,
            "final_metrics": asdict(self.final_metrics),
            "findings": [asdict(finding) for finding in self.findings],
        }


def assess_metrics(metrics: list[Metrics]) -> list[HealthFinding]:
    if not metrics:
        return [
            HealthFinding(
                code="no_metrics",
                severity="critical",
                day=0,
                description="No metrics were produced.",
            )
        ]

    final = metrics[-1]
    findings: list[HealthFinding] = []

    if final.population <= 0:
        findings.append(
            HealthFinding(
                code="population_collapse",
                severity="critical",
                day=final.day,
                description="Population reached zero.",
            )
        )

    if final.average_need < 0.35:
        findings.append(
            HealthFinding(
                code="low_wellbeing",
                severity="critical",
                day=final.day,
                description=f"Average need fell to {final.average_need:.3f}.",
            )
        )
    elif final.average_need < 0.45:
        findings.append(
            HealthFinding(
                code="strained_wellbeing",
                severity="warning",
                day=final.day,
                description=f"Average need is strained at {final.average_need:.3f}.",
            )
        )

    if final.average_trust < 0.25:
        findings.append(
            HealthFinding(
                code="social_fracture",
                severity="critical",
                day=final.day,
                description=f"Average trust fell to {final.average_trust:.3f}.",
            )
        )
    elif final.average_trust < 0.45:
        findings.append(
            HealthFinding(
                code="weak_trust",
                severity="warning",
                day=final.day,
                description=f"Average trust is weak at {final.average_trust:.3f}.",
            )
        )

    if final.average_reputation < 0.25:
        findings.append(
            HealthFinding(
                code="reputation_collapse",
                severity="critical",
                day=final.day,
                description=f"Average reputation fell to {final.average_reputation:.3f}.",
            )
        )
    elif final.average_reputation < 0.40:
        findings.append(
            HealthFinding(
                code="weak_reputation",
                severity="warning",
                day=final.day,
                description=f"Average reputation is weak at {final.average_reputation:.3f}.",
            )
        )

    if final.institutional_cohesion < 0.25:
        findings.append(
            HealthFinding(
                code="institutional_collapse",
                severity="critical",
                day=final.day,
                description=f"Institutional cohesion fell to {final.institutional_cohesion:.3f}.",
            )
        )
    elif final.institutional_cohesion < 0.40:
        findings.append(
            HealthFinding(
                code="weak_institutions",
                severity="warning",
                day=final.day,
                description=f"Institutional cohesion is weak at {final.institutional_cohesion:.3f}.",
            )
        )

    recent = metrics[-min(30, len(metrics)):]
    if all(item.food <= 0.05 for item in recent):
        findings.append(
            HealthFinding(
                code="persistent_food_scarcity",
                severity="warning",
                day=final.day,
                description="Food stayed near zero for the recent window.",
            )
        )

    if all(item.materials <= 0.05 for item in recent):
        findings.append(
            HealthFinding(
                code="materials_depleted",
                severity="info",
                day=final.day,
                description="Materials stayed near zero for the recent window.",
            )
        )

    crisis_warning_threshold = max(5, int(final.day * 0.05))
    if final.crisis_events > crisis_warning_threshold:
        findings.append(
            HealthFinding(
                code="crisis_events",
                severity="warning",
                day=final.day,
                description=f"{final.crisis_events} crisis events were recorded.",
            )
        )
    elif final.crisis_events > 0:
        findings.append(
            HealthFinding(
                code="transient_crises",
                severity="info",
                day=final.day,
                description=f"{final.crisis_events} crisis events were recorded but did not dominate the run.",
            )
        )

    if not findings:
        findings.append(
            HealthFinding(
                code="stable",
                severity="info",
                day=final.day,
                description="No collapse or major instability detected.",
            )
        )

    return findings
