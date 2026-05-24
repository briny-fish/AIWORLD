from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CounterfactualProbeRecord:
    day: int
    agent_id: str
    agent_name: str
    baseline_action: str
    proposed_action: str
    recommendation: str
    score_delta: float
    baseline_score: float
    proposed_score: float
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CounterfactualBucket:
    key: str
    label: str
    total: int
    accepted: int
    rejected: int
    average_score_delta: float
    worst_score_delta: float
    best_score_delta: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CounterfactualAssessment:
    total: int
    accepted: int
    rejected: int
    acceptance_rate: float
    average_score_delta: float
    worst_score_delta: float
    best_score_delta: float
    worst_record: CounterfactualProbeRecord | None
    by_agent: list[CounterfactualBucket]
    by_action_pair: list[CounterfactualBucket]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_counterfactual_trace(
    cognition_trace: list[dict[str, Any]],
) -> CounterfactualAssessment:
    records = [_record_from_trace(item) for item in cognition_trace]
    records = [record for record in records if record is not None]
    total = len(records)
    if total == 0:
        return CounterfactualAssessment(
            total=0,
            accepted=0,
            rejected=0,
            acceptance_rate=0.0,
            average_score_delta=0.0,
            worst_score_delta=0.0,
            best_score_delta=0.0,
            worst_record=None,
            by_agent=[],
            by_action_pair=[],
            summary="No counterfactual cognition probes were recorded.",
        )

    accepted = sum(1 for record in records if record.recommendation == "proposed")
    rejected = sum(1 for record in records if record.recommendation == "baseline")
    average_score_delta = _average([record.score_delta for record in records])
    worst_record = min(records, key=lambda record: record.score_delta)
    best_score_delta = max(record.score_delta for record in records)
    return CounterfactualAssessment(
        total=total,
        accepted=accepted,
        rejected=rejected,
        acceptance_rate=round(accepted / total, 3),
        average_score_delta=average_score_delta,
        worst_score_delta=round(worst_record.score_delta, 4),
        best_score_delta=round(best_score_delta, 4),
        worst_record=worst_record,
        by_agent=_buckets(records, key_fn=lambda record: record.agent_id, label_fn=lambda record: record.agent_name),
        by_action_pair=_buckets(
            records,
            key_fn=lambda record: f"{record.baseline_action}->{record.proposed_action}",
            label_fn=lambda record: f"{record.baseline_action} -> {record.proposed_action}",
        ),
        summary=_summary(total, accepted, rejected, average_score_delta, worst_record),
    )


def _record_from_trace(item: dict[str, Any]) -> CounterfactualProbeRecord | None:
    counterfactual = item.get("counterfactual") or {}
    if not counterfactual:
        return None
    baseline = counterfactual.get("baseline") or {}
    proposed = counterfactual.get("proposed") or {}
    return CounterfactualProbeRecord(
        day=int(item.get("day", 0)),
        agent_id=str(item.get("agent_id") or ""),
        agent_name=str(item.get("agent_name") or ""),
        baseline_action=str(baseline.get("action") or ""),
        proposed_action=str(proposed.get("action") or ""),
        recommendation=str(counterfactual.get("recommendation") or ""),
        score_delta=round(float(counterfactual.get("score_delta", 0.0)), 4),
        baseline_score=round(float(baseline.get("score", 0.0)), 4),
        proposed_score=round(float(proposed.get("score", 0.0)), 4),
        status=str(item.get("status") or ""),
    )


def _buckets(
    records: list[CounterfactualProbeRecord],
    key_fn,
    label_fn,
) -> list[CounterfactualBucket]:
    grouped: dict[str, list[CounterfactualProbeRecord]] = {}
    labels: dict[str, str] = {}
    for record in records:
        key = key_fn(record)
        grouped.setdefault(key, []).append(record)
        labels.setdefault(key, label_fn(record))

    buckets = []
    for key, bucket_records in grouped.items():
        deltas = [record.score_delta for record in bucket_records]
        accepted = sum(1 for record in bucket_records if record.recommendation == "proposed")
        rejected = sum(1 for record in bucket_records if record.recommendation == "baseline")
        buckets.append(
            CounterfactualBucket(
                key=key,
                label=labels[key],
                total=len(bucket_records),
                accepted=accepted,
                rejected=rejected,
                average_score_delta=_average(deltas),
                worst_score_delta=round(min(deltas), 4),
                best_score_delta=round(max(deltas), 4),
            )
        )
    return sorted(
        buckets,
        key=lambda bucket: (-bucket.total, bucket.average_score_delta, bucket.label),
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _summary(
    total: int,
    accepted: int,
    rejected: int,
    average_score_delta: float,
    worst_record: CounterfactualProbeRecord,
) -> str:
    return (
        f"Counterfactual probes accepted {accepted}/{total} proposals "
        f"and rejected {rejected}; average score delta {_signed(average_score_delta)}. "
        f"Worst case was {worst_record.agent_name} on day {worst_record.day}: "
        f"{worst_record.baseline_action} -> {worst_record.proposed_action} "
        f"with delta {_signed(worst_record.score_delta)}."
    )


def _signed(value: float) -> str:
    return f"{value:+g}" if value else "0"
