from __future__ import annotations

from collections.abc import Iterable

from .health import RunReport, assess_metrics
from .interventions import Intervention
from .simulation import Simulation


def run_experiment(
    seeds: Iterable[int],
    days: int,
    interventions: Iterable[Intervention] = (),
    world_preset: str = "base",
) -> list[RunReport]:
    intervention_list = list(interventions)
    reports: list[RunReport] = []
    for seed in seeds:
        simulation = Simulation(seed=seed, world_preset=world_preset)
        metrics = simulation.run(days=days, interventions=intervention_list)
        reports.append(
            RunReport(
                seed=seed,
                days=days,
                final_metrics=metrics[-1],
                findings=assess_metrics(metrics),
            )
        )
    return reports
