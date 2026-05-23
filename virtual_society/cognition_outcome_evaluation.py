from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .model import Metrics


COMPARISON_METRICS = [
    "population",
    "food",
    "materials",
    "shelter",
    "average_need",
    "average_trust",
    "average_reputation",
    "institutional_cohesion",
    "crisis_events",
]


@dataclass(frozen=True)
class OutcomeWindow:
    label: str
    day: int
    deltas: dict[str, float]
    signal: str


@dataclass(frozen=True)
class CognitionOutcome:
    day: int
    agent_id: str
    agent_name: str
    cognition_signal: str
    outcome_signal: str
    windows: list[OutcomeWindow]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_cognition_outcomes(
    metrics: list[Metrics],
    baseline_metrics: list[Metrics] | None,
    cognition_impacts: list[dict[str, Any]],
    offsets: tuple[int, ...] = (0, 1, 3, 7),
) -> list[CognitionOutcome]:
    """Compare post-cognition run metrics against a deterministic baseline."""
    if baseline_metrics is None or not metrics or not baseline_metrics:
        return []

    run_by_day = {item.day: item for item in metrics}
    baseline_by_day = {item.day: item for item in baseline_metrics}
    final_day = min(metrics[-1].day, baseline_metrics[-1].day)
    outcomes: list[CognitionOutcome] = []

    for impact in cognition_impacts:
        day = int(impact.get("day", 0))
        windows = _windows_for_impact(
            day,
            final_day,
            run_by_day,
            baseline_by_day,
            offsets,
        )
        if not windows:
            continue
        outcome_signal = windows[-1].signal
        outcomes.append(
            CognitionOutcome(
                day=day,
                agent_id=str(impact.get("agent_id") or ""),
                agent_name=str(impact.get("agent_name") or ""),
                cognition_signal=str(impact.get("signal") or ""),
                outcome_signal=outcome_signal,
                windows=windows,
                summary=_summary(
                    day,
                    str(impact.get("agent_name") or ""),
                    str(impact.get("signal") or ""),
                    outcome_signal,
                    windows,
                ),
            )
        )
    return outcomes


def _windows_for_impact(
    day: int,
    final_day: int,
    run_by_day: dict[int, Metrics],
    baseline_by_day: dict[int, Metrics],
    offsets: tuple[int, ...],
) -> list[OutcomeWindow]:
    target_days = []
    for offset in offsets:
        target_days.append(min(final_day, day + offset))
    target_days.append(final_day)

    windows = []
    seen = set()
    for target_day in target_days:
        if target_day in seen:
            continue
        seen.add(target_day)
        run_metric = run_by_day.get(target_day)
        baseline_metric = baseline_by_day.get(target_day)
        if run_metric is None or baseline_metric is None:
            continue
        label = "final" if target_day == final_day else f"+{target_day - day}d"
        deltas = _metric_deltas(run_metric, baseline_metric)
        windows.append(
            OutcomeWindow(
                label=label,
                day=target_day,
                deltas=deltas,
                signal=_classify_deltas(deltas),
            )
        )
    return windows


def _metric_deltas(run_metric: Metrics, baseline_metric: Metrics) -> dict[str, float]:
    run = asdict(run_metric)
    baseline = asdict(baseline_metric)
    return {
        key: round(float(run[key]) - float(baseline[key]), 3)
        for key in COMPARISON_METRICS
        if key in run and key in baseline
    }


def _classify_deltas(deltas: dict[str, float]) -> str:
    social = (
        deltas.get("average_need", 0.0)
        + deltas.get("average_trust", 0.0)
        + deltas.get("institutional_cohesion", 0.0)
    )
    resources = (
        deltas.get("food", 0.0)
        + deltas.get("materials", 0.0)
        + deltas.get("shelter", 0.0)
    )

    social_threshold = 0.003
    resource_threshold = 0.15
    if abs(social) <= social_threshold and abs(resources) <= resource_threshold:
        return "outcome_neutral"
    if social < -social_threshold and resources > resource_threshold:
        return "mixed_resource_gain_social_cost"
    if social > social_threshold and resources < -resource_threshold:
        return "mixed_social_gain_resource_cost"
    if social > social_threshold:
        return "outcome_social_gain"
    if social < -social_threshold:
        return "outcome_social_cost"
    if resources > resource_threshold:
        return "outcome_resource_gain"
    if resources < -resource_threshold:
        return "outcome_resource_cost"
    return "outcome_neutral"


def _summary(
    day: int,
    agent_name: str,
    cognition_signal: str,
    outcome_signal: str,
    windows: list[OutcomeWindow],
) -> str:
    final = windows[-1]
    final_deltas = final.deltas
    return (
        f"Generated cognition for {agent_name} on day {day} had cognition "
        f"signal {cognition_signal} and final outcome signal {outcome_signal}; "
        f"final deltas: average_need {_signed(final_deltas.get('average_need', 0.0))}, "
        f"average_trust {_signed(final_deltas.get('average_trust', 0.0))}, "
        f"food {_signed(final_deltas.get('food', 0.0))}, "
        f"materials {_signed(final_deltas.get('materials', 0.0))}, "
        f"shelter {_signed(final_deltas.get('shelter', 0.0))}."
    )


def _signed(value: float) -> str:
    return f"{value:+g}" if value else "0"
