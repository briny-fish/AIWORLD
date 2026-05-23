from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from .model import Metrics, Plan, WorldState
from .simulation import Simulation


@dataclass(frozen=True)
class PlanProbeResult:
    label: str
    action: str
    target_id: str | None
    reason: str
    score: float
    metrics: dict[str, Any]


@dataclass(frozen=True)
class PlanCounterfactualComparison:
    horizon_days: int
    baseline: PlanProbeResult
    proposed: PlanProbeResult
    score_delta: float
    recommendation: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_plan_counterfactuals(
    world: WorldState,
    agent_id: str,
    baseline_plan: Plan,
    proposed_plan: Plan,
    horizon_days: int = 3,
    seed: int = 9173,
    reject_threshold: float = 0.02,
) -> PlanCounterfactualComparison:
    """Probe two candidate plans from the same world snapshot.

    This is an acceptance-policy instrument, not a replacement simulation. It
    applies one candidate plan in a copied world, then lets deterministic rule
    cognition advance the world for a short horizon. The real world is never
    mutated by this function.
    """

    if horizon_days < 0:
        raise ValueError("horizon_days must be >= 0")
    if reject_threshold < 0:
        raise ValueError("reject_threshold must be >= 0")

    baseline = _probe_plan(world, agent_id, baseline_plan, "baseline", horizon_days, seed)
    proposed = _probe_plan(world, agent_id, proposed_plan, "proposed", horizon_days, seed)
    score_delta = round(proposed.score - baseline.score, 4)
    recommendation = "proposed"
    reason = (
        f"counterfactual accepted: proposed score {proposed.score:.4f} "
        f"vs baseline {baseline.score:.4f}"
    )

    baseline_crises = int(baseline.metrics.get("crisis_events", 0))
    proposed_crises = int(proposed.metrics.get("crisis_events", 0))
    if proposed_crises > baseline_crises:
        recommendation = "baseline"
        reason = (
            "counterfactual rejected: proposed plan increases crisis events "
            f"from {baseline_crises} to {proposed_crises}"
        )
    elif score_delta < -reject_threshold:
        recommendation = "baseline"
        reason = (
            "counterfactual rejected: proposed score trails baseline by "
            f"{abs(score_delta):.4f}"
        )

    return PlanCounterfactualComparison(
        horizon_days=horizon_days,
        baseline=baseline,
        proposed=proposed,
        score_delta=score_delta,
        recommendation=recommendation,
        reason=reason,
    )


def _probe_plan(
    world: WorldState,
    agent_id: str,
    plan: Plan,
    label: str,
    horizon_days: int,
    seed: int,
) -> PlanProbeResult:
    probe_world = deepcopy(world)
    simulation = Simulation(seed=seed, world=probe_world)
    agent = next((candidate for candidate in simulation.world.agents if candidate.id == agent_id), None)
    if agent is None:
        raise ValueError(f"Unknown agent id: {agent_id}")

    validated_plan = simulation._validate_plan(agent, plan)
    simulation._record_plan(agent, plan, validated_plan)
    simulation._apply_action(agent, validated_plan)
    agent.needs.clamp()
    simulation._sync_world_resources()

    metrics = simulation.run(horizon_days)[-1] if horizon_days else simulation.metrics()
    score = _score_metrics(metrics)
    return PlanProbeResult(
        label=label,
        action=validated_plan.action.value,
        target_id=validated_plan.target_id,
        reason=validated_plan.reason,
        score=score,
        metrics=asdict(metrics),
    )


def _score_metrics(metrics: Metrics) -> float:
    population = max(metrics.population, 1)
    food_score = min(metrics.food / max(population * 1.8, 1.0), 1.0)
    material_score = min(metrics.materials / max(population * 0.8, 1.0), 1.0)
    shelter_score = min(metrics.shelter / max(population * 0.9, 1.0), 1.0)
    social_score = (
        metrics.average_need * 3.0
        + metrics.average_trust
        + metrics.average_reputation * 0.8
        + metrics.institutional_cohesion
    )
    resource_score = food_score * 1.8 + material_score * 0.7 + shelter_score * 0.9
    crisis_penalty = metrics.crisis_events * 2.0
    return round(social_score + resource_score - crisis_penalty, 4)
