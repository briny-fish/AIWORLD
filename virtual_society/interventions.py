from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Intervention:
    day: int
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    actor_id: str = "observer"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Intervention":
        day = int(data["day"])
        kind = str(data["kind"])
        params = dict(data.get("params", {}))
        reason = str(data.get("reason", ""))
        actor_id = str(data.get("actor_id", "observer"))
        if day < 1:
            raise ValueError("Intervention day must be >= 1")
        if not kind:
            raise ValueError("Intervention kind is required")
        return cls(day=day, kind=kind, params=params, reason=reason, actor_id=actor_id)


def load_interventions(path: str | Path) -> list[Intervention]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Intervention file must contain a JSON list")
    return [Intervention.from_dict(item) for item in raw]


def group_interventions(interventions: Iterable[Intervention]) -> dict[int, list[Intervention]]:
    grouped: dict[int, list[Intervention]] = {}
    for intervention in interventions:
        grouped.setdefault(intervention.day, []).append(intervention)
    return grouped

