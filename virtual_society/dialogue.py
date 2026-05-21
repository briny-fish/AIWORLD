from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from .dialogue_contract import DialogueProposal
from .model import Agent, WorldState


class DialogueProvider(Protocol):
    def propose_dialogue(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline_dialogue: str,
    ) -> DialogueProposal:
        """Return a social dialogue proposal grounded by simulation evidence."""


class RuleBasedDialogue:
    """Deterministic dialogue provider and generated dialogue fallback."""

    def propose_dialogue(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline_dialogue: str,
    ) -> DialogueProposal:
        return DialogueProposal(text=baseline_dialogue, focus="routine")


@dataclass
class HybridDialogueConfig:
    agent_ids: set[str] | None = None
    min_day: int = 1
    max_calls: int = 4
    max_failures: int = 2
    trace_limit: int = 60


@dataclass
class HybridDialogueStats:
    llm_attempts: int = 0
    llm_successes: int = 0
    llm_failures: int = 0
    fallback_calls: int = 0
    skipped_calls: int = 0
    last_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HybridDialogueTrace:
    day: int
    speaker_id: str
    speaker_name: str
    partner_id: str
    partner_name: str
    status: str
    baseline_dialogue: str
    proposed_dialogue: str | None
    used_dialogue: str
    focus: str
    memory_refs: list[int]
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class HybridDialogue:
    """Budgeted generated dialogue with deterministic fallback."""

    def __init__(
        self,
        primary: DialogueProvider,
        fallback: DialogueProvider | None = None,
        config: HybridDialogueConfig | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback if fallback is not None else RuleBasedDialogue()
        self.config = config if config is not None else HybridDialogueConfig()
        self.stats = HybridDialogueStats()
        self.trace: list[HybridDialogueTrace] = []

    def propose_dialogue(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline_dialogue: str,
    ) -> DialogueProposal:
        if not self._should_call_primary(speaker, world.day):
            self.stats.skipped_calls += 1
            self.stats.fallback_calls += 1
            return self.fallback.propose_dialogue(
                speaker,
                partner,
                world,
                baseline_dialogue,
            )

        baseline = self.fallback.propose_dialogue(
            speaker,
            partner,
            world,
            baseline_dialogue,
        )
        self.stats.llm_attempts += 1
        try:
            proposal = self._call_primary(speaker, partner, world, baseline)
        except Exception as exc:
            self.stats.llm_failures += 1
            self.stats.fallback_calls += 1
            self._remember_error(exc)
            self._record_trace(
                speaker,
                partner,
                world.day,
                "fallback_after_error",
                baseline,
                None,
                baseline,
                str(exc),
            )
            return baseline

        self.stats.llm_successes += 1
        self._record_trace(
            speaker,
            partner,
            world.day,
            "primary",
            baseline,
            proposal,
            proposal,
            None,
        )
        return proposal

    def _should_call_primary(self, speaker: Agent, day: int) -> bool:
        if self.config.max_calls <= 0:
            return False
        if self.stats.llm_attempts >= self.config.max_calls:
            return False
        if self.stats.llm_failures >= self.config.max_failures:
            return False
        if self.config.agent_ids is not None and speaker.id not in self.config.agent_ids:
            return False
        return day >= self.config.min_day

    def _call_primary(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline: DialogueProposal,
    ) -> DialogueProposal:
        baseline_aware = getattr(self.primary, "propose_dialogue_with_baseline", None)
        if callable(baseline_aware):
            return baseline_aware(speaker, partner, world, baseline)
        return self.primary.propose_dialogue(speaker, partner, world, baseline.text)

    def _remember_error(self, exc: Exception) -> None:
        self.stats.last_errors.append(str(exc))
        del self.stats.last_errors[:-5]

    def _record_trace(
        self,
        speaker: Agent,
        partner: Agent,
        day: int,
        status: str,
        baseline: DialogueProposal,
        proposed: DialogueProposal | None,
        used: DialogueProposal,
        error: str | None,
    ) -> None:
        self.trace.append(
            HybridDialogueTrace(
                day=day,
                speaker_id=speaker.id,
                speaker_name=speaker.name,
                partner_id=partner.id,
                partner_name=partner.name,
                status=status,
                baseline_dialogue=baseline.text,
                proposed_dialogue=proposed.text if proposed is not None else None,
                used_dialogue=used.text,
                focus=used.focus,
                memory_refs=list(proposed.memory_refs) if proposed is not None else [],
                error=error,
            )
        )
        if self.config.trace_limit == 0:
            self.trace.clear()
        elif self.config.trace_limit > 0:
            del self.trace[: -self.config.trace_limit]
