from __future__ import annotations

from dataclasses import dataclass, field

from .cognition import CognitionProvider, RuleBasedCognition
from .model import Agent, Plan, WorldState


@dataclass
class HybridCognitionConfig:
    agent_ids: set[str] | None = None
    every_days: int = 7
    min_day: int = 1
    max_calls: int = 10
    max_failures: int = 3


@dataclass
class HybridCognitionStats:
    llm_attempts: int = 0
    llm_successes: int = 0
    llm_failures: int = 0
    fallback_calls: int = 0
    skipped_calls: int = 0
    last_errors: list[str] = field(default_factory=list)


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

    def propose_plan(self, agent: Agent, world: WorldState) -> Plan:
        if not self._should_call_primary(agent, world):
            self.stats.skipped_calls += 1
            self.stats.fallback_calls += 1
            return self.fallback.propose_plan(agent, world)

        self.stats.llm_attempts += 1
        try:
            plan = self.primary.propose_plan(agent, world)
        except Exception as exc:
            self.stats.llm_failures += 1
            self.stats.fallback_calls += 1
            self._remember_error(exc)
            return self.fallback.propose_plan(agent, world)

        self.stats.llm_successes += 1
        return plan

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

