from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .cognition import CognitionProvider, RuleBasedCognition
from .model import Action, Agent, Plan, WorldState


@dataclass
class HybridCognitionConfig:
    agent_ids: set[str] | None = None
    every_days: int = 7
    min_day: int = 1
    max_calls: int = 10
    max_failures: int = 3
    trace_limit: int = 100
    guard_rest_overrides: bool = True


@dataclass
class HybridCognitionStats:
    llm_attempts: int = 0
    llm_successes: int = 0
    llm_failures: int = 0
    fallback_calls: int = 0
    skipped_calls: int = 0
    last_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HybridCognitionTrace:
    day: int
    agent_id: str
    agent_name: str
    status: str
    baseline_plan: dict
    proposed_plan: dict | None
    used_plan: dict
    diverged_from_baseline: bool
    proposed_diverged_from_baseline: bool = False
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class HybridCognition:
    """Budgeted LLM cognition with deterministic fallback."""

    def __init__(
        self,
        primary: CognitionProvider,
        fallback: CognitionProvider | None = None,
        config: HybridCognitionConfig | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback if fallback is not None else RuleBasedCognition()
        self.config = config if config is not None else HybridCognitionConfig()
        self.stats = HybridCognitionStats()
        self.trace: list[HybridCognitionTrace] = []

    def propose_plan(self, agent: Agent, world: WorldState) -> Plan:
        if not self._should_call_primary(agent, world):
            self.stats.skipped_calls += 1
            self.stats.fallback_calls += 1
            return self.fallback.propose_plan(agent, world)

        baseline_plan = self.fallback.propose_plan(agent, world)
        self.stats.llm_attempts += 1
        try:
            plan = self._call_primary(agent, world, baseline_plan)
        except Exception as exc:
            self.stats.llm_failures += 1
            self.stats.fallback_calls += 1
            self._remember_error(exc)
            self._record_trace(
                agent=agent,
                world=world,
                status="fallback_after_error",
                baseline_plan=baseline_plan,
                proposed_plan=None,
                used_plan=baseline_plan,
                error=str(exc),
            )
            return baseline_plan

        self.stats.llm_successes += 1
        used_plan, status, policy_note = self._apply_acceptance_policy(
            agent,
            world,
            baseline_plan,
            plan,
        )
        self._record_trace(
            agent=agent,
            world=world,
            status=status,
            baseline_plan=baseline_plan,
            proposed_plan=plan,
            used_plan=used_plan,
            error=policy_note,
        )
        return used_plan

    def _call_primary(
        self,
        agent: Agent,
        world: WorldState,
        baseline_plan: Plan,
    ) -> Plan:
        baseline_aware = getattr(self.primary, "propose_plan_with_baseline", None)
        if callable(baseline_aware):
            return baseline_aware(agent, world, baseline_plan)
        return self.primary.propose_plan(agent, world)

    def _apply_acceptance_policy(
        self,
        agent: Agent,
        world: WorldState,
        baseline_plan: Plan,
        proposed_plan: Plan,
    ) -> tuple[Plan, str, str | None]:
        if not self.config.guard_rest_overrides:
            return proposed_plan, "primary", None

        productive_actions = {Action.FARM, Action.GATHER, Action.HAUL, Action.REPAIR}
        if (
            proposed_plan.action != Action.REST
            or baseline_plan.action not in productive_actions
            or not _shared_resource_pressure(world)
            or _rest_is_required(agent, world)
        ):
            return proposed_plan, "primary", None

        return (
            baseline_plan,
            "baseline_after_policy",
            (
                "rest override rejected: shared pressure is active and the agent "
                "is not at the exhaustion threshold or just blocked by exhaustion"
            ),
        )

    def _should_call_primary(self, agent: Agent, world: WorldState) -> bool:
        if self.config.max_calls <= 0:
            return False
        if self.stats.llm_attempts >= self.config.max_calls:
            return False
        if self.stats.llm_failures >= self.config.max_failures:
            return False
        if self.config.agent_ids is not None and agent.id not in self.config.agent_ids:
            return False
        if world.day < self.config.min_day:
            return False
        if self.config.every_days < 1:
            return False
        return world.day % self.config.every_days == 0

    def _remember_error(self, exc: Exception) -> None:
        self.stats.last_errors.append(str(exc))
        del self.stats.last_errors[:-5]

    def _record_trace(
        self,
        agent: Agent,
        world: WorldState,
        status: str,
        baseline_plan: Plan,
        proposed_plan: Plan | None,
        used_plan: Plan,
        error: str | None,
    ) -> None:
        self.trace.append(
            HybridCognitionTrace(
                day=world.day,
                agent_id=agent.id,
                agent_name=agent.name,
                status=status,
                baseline_plan=_plan_dict(baseline_plan),
                proposed_plan=_plan_dict(proposed_plan) if proposed_plan is not None else None,
                used_plan=_plan_dict(used_plan),
                diverged_from_baseline=_plan_differs(used_plan, baseline_plan),
                proposed_diverged_from_baseline=(
                    _plan_differs(proposed_plan, baseline_plan)
                    if proposed_plan is not None
                    else False
                ),
                error=error,
            )
        )
        if self.config.trace_limit == 0:
            self.trace.clear()
        elif self.config.trace_limit > 0:
            del self.trace[: -self.config.trace_limit]


def _plan_dict(plan: Plan) -> dict:
    return {
        "action": plan.action.value,
        "priority": plan.priority,
        "reason": plan.reason,
        "target_id": plan.target_id,
        "horizon_days": plan.horizon_days,
    }


def _plan_differs(first: Plan, second: Plan) -> bool:
    return (
        first.action != second.action
        or first.target_id != second.target_id
        or first.horizon_days != second.horizon_days
    )


def _shared_resource_pressure(world: WorldState) -> bool:
    food_pressure = world.population * world.rules.food_per_agent * 1.15
    material_floor = world.population * 0.35
    shelter_floor = world.population * world.rules.shelter_safety_ratio
    return (
        world.resources.get("food", 0.0) < food_pressure
        or world.resources.get("materials", 0.0) < material_floor
        or world.resources.get("shelter", 0.0) < shelter_floor
    )


def _rest_is_required(agent: Agent, world: WorldState) -> bool:
    if agent.needs.energy <= world.rules.exhaustion_work_threshold:
        return True
    if not agent.plan_history:
        return False
    recent_plan_text = " ".join(agent.plan_history[-4:]).lower()
    return "blocked by exhaustion" in recent_plan_text
