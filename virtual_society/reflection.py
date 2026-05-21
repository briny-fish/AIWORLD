from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from .generative_memory import build_reflection
from .model import Agent, WorldState
from .reflection_contract import ReflectionProposal


class ReflectionProvider(Protocol):
    def propose_reflection(
        self,
        agent: Agent,
        world: WorldState,
        current_day: int,
        lookback_days: int,
    ) -> ReflectionProposal:
        """Return an agent reflection proposal grounded by simulation evidence."""


class RuleBasedReflection:
    """Deterministic reflection provider used for long runs and fallback."""

    def propose_reflection(
        self,
        agent: Agent,
        world: WorldState,
        current_day: int,
        lookback_days: int,
    ) -> ReflectionProposal:
        return ReflectionProposal(
            summary=build_reflection(agent, current_day, lookback_days),
            focus="routine",
        )


@dataclass
class HybridReflectionConfig:
    agent_ids: set[str] | None = None
    min_day: int = 1
    max_calls: int = 4
    max_failures: int = 2
    trace_limit: int = 60


@dataclass
class HybridReflectionStats:
    llm_attempts: int = 0
    llm_successes: int = 0
    llm_failures: int = 0
    fallback_calls: int = 0
    skipped_calls: int = 0
    last_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HybridReflectionTrace:
    day: int
    agent_id: str
    agent_name: str
    status: str
    baseline_reflection: str
    proposed_reflection: str | None
    used_reflection: str
    focus: str
    memory_refs: list[int]
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class HybridReflection:
    """Budgeted generated reflection with deterministic fallback."""

    def __init__(
        self,
        primary: ReflectionProvider,
        fallback: ReflectionProvider | None = None,
        config: HybridReflectionConfig | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback if fallback is not None else RuleBasedReflection()
        self.config = config if config is not None else HybridReflectionConfig()
        self.stats = HybridReflectionStats()
        self.trace: list[HybridReflectionTrace] = []

    def propose_reflection(
        self,
        agent: Agent,
        world: WorldState,
        current_day: int,
        lookback_days: int,
    ) -> ReflectionProposal:
        if not self._should_call_primary(agent, current_day):
            self.stats.skipped_calls += 1
            self.stats.fallback_calls += 1
            return self.fallback.propose_reflection(
                agent,
                world,
                current_day,
                lookback_days,
            )

        baseline = self.fallback.propose_reflection(
            agent,
            world,
            current_day,
            lookback_days,
        )
        self.stats.llm_attempts += 1
        try:
            proposal = self._call_primary(
                agent,
                world,
                current_day,
                lookback_days,
                baseline,
            )
        except Exception as exc:
            self.stats.llm_failures += 1
            self.stats.fallback_calls += 1
            self._remember_error(exc)
            self._record_trace(
                agent,
                current_day,
                "fallback_after_error",
                baseline,
                None,
                baseline,
                str(exc),
            )
            return baseline

        self.stats.llm_successes += 1
        self._record_trace(
            agent,
            current_day,
            "primary",
            baseline,
            proposal,
            proposal,
            None,
        )
        return proposal

    def _should_call_primary(self, agent: Agent, current_day: int) -> bool:
        if self.config.max_calls <= 0:
            return False
        if self.stats.llm_attempts >= self.config.max_calls:
            return False
        if self.stats.llm_failures >= self.config.max_failures:
            return False
        if self.config.agent_ids is not None and agent.id not in self.config.agent_ids:
            return False
        return current_day >= self.config.min_day

    def _call_primary(
        self,
        agent: Agent,
        world: WorldState,
        current_day: int,
        lookback_days: int,
        baseline: ReflectionProposal,
    ) -> ReflectionProposal:
        baseline_aware = getattr(
            self.primary,
            "propose_reflection_with_baseline",
            None,
        )
        if callable(baseline_aware):
            return baseline_aware(
                agent,
                world,
                current_day,
                lookback_days,
                baseline,
            )
        return self.primary.propose_reflection(
            agent,
            world,
            current_day,
            lookback_days,
        )

    def _remember_error(self, exc: Exception) -> None:
        self.stats.last_errors.append(str(exc))
        del self.stats.last_errors[:-5]

    def _record_trace(
        self,
        agent: Agent,
        day: int,
        status: str,
        baseline: ReflectionProposal,
        proposed: ReflectionProposal | None,
        used: ReflectionProposal,
        error: str | None,
    ) -> None:
        self.trace.append(
            HybridReflectionTrace(
                day=day,
                agent_id=agent.id,
                agent_name=agent.name,
                status=status,
                baseline_reflection=baseline.summary,
                proposed_reflection=proposed.summary if proposed is not None else None,
                used_reflection=used.summary,
                focus=used.focus,
                memory_refs=list(proposed.memory_refs) if proposed is not None else [],
                error=error,
            )
        )
        if self.config.trace_limit == 0:
            self.trace.clear()
        elif self.config.trace_limit > 0:
            del self.trace[: -self.config.trace_limit]
