import unittest

from virtual_society.experiment import run_experiment
from virtual_society.interventions import Intervention
from virtual_society import Simulation


class SimulationTests(unittest.TestCase):
    def test_simulation_is_deterministic_for_same_seed(self) -> None:
        first = Simulation(seed=42).run(30)
        second = Simulation(seed=42).run(30)

        self.assertEqual(first, second)

    def test_simulation_runs_without_collapsing_for_initial_month(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(30)
        final = metrics[-1]

        self.assertEqual(final.population, 6)
        self.assertGreaterEqual(final.food, 0)
        self.assertGreaterEqual(final.materials, 0)
        self.assertGreaterEqual(final.shelter, 0)
        self.assertGreater(final.average_need, 0.35)

    def test_simulation_runs_for_one_year(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(365)
        final = metrics[-1]

        self.assertEqual(final.population, 6)
        self.assertGreaterEqual(final.food, 0)
        self.assertGreaterEqual(final.materials, 0)
        self.assertGreaterEqual(final.shelter, 0)
        self.assertGreater(final.average_need, 0.35)

    def test_observer_can_inject_resources(self) -> None:
        simulation = Simulation(seed=7)
        before = simulation.world.resources["food"]

        simulation.inject_resource("food", 5.0, reason="test")

        self.assertEqual(simulation.world.resources["food"], before + 5.0)
        self.assertEqual(simulation.world.event_log[-1].kind, "intervention")

    def test_scheduled_interventions_are_deterministic(self) -> None:
        interventions = [
            Intervention(
                day=10,
                kind="disaster",
                reason="test storm",
                params={"name": "storm", "severity": 0.3},
            ),
            Intervention(
                day=12,
                kind="resource",
                reason="relief",
                params={"resource": "food", "amount": 5},
            ),
        ]

        first = Simulation(seed=11).run(40, interventions=interventions)
        second = Simulation(seed=11).run(40, interventions=interventions)

        self.assertEqual(first, second)

    def test_disaster_reduces_resources_and_records_event(self) -> None:
        simulation = Simulation(seed=7)
        before_food = simulation.world.resources["food"]

        simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="disaster",
                    params={"name": "storm", "severity": 0.5},
                )
            ],
        )

        self.assertLess(simulation.world.resources["food"], before_food)
        self.assertEqual(simulation.world.event_log[0].kind, "disaster")

    def test_new_agent_intervention_increases_population(self) -> None:
        simulation = Simulation(seed=7)

        metrics = simulation.run(
            2,
            interventions=[
                Intervention(
                    day=1,
                    kind="new_agent",
                    params={"name": "Gale", "role": "scout"},
                )
            ],
        )

        self.assertEqual(metrics[-1].population, 7)
        self.assertEqual(simulation.world.event_log[0].kind, "arrival")

    def test_edict_intervention_changes_world_rules(self) -> None:
        simulation = Simulation(seed=7)

        simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="edict",
                    params={"rule": "food_per_agent", "value": 0.8},
                )
            ],
        )

        self.assertEqual(simulation.world.rules.food_per_agent, 0.8)
        self.assertEqual(simulation.world.event_log[0].kind, "edict")

    def test_experiment_returns_report_for_each_seed(self) -> None:
        reports = run_experiment(seeds=[1, 2, 3], days=30)

        self.assertEqual([report.seed for report in reports], [1, 2, 3])
        self.assertTrue(all(report.findings for report in reports))


if __name__ == "__main__":
    unittest.main()
