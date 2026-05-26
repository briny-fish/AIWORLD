import unittest

from virtual_society.experiment import run_experiment
from virtual_society.interventions import Intervention
from virtual_society import Simulation
from virtual_society.cognition import RuleBasedCognition
from virtual_society.model import Action, Plan


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

    def test_broadcast_intent_can_target_agent_memory(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.day = 1
        target = simulation.world.agents[0]
        other = simulation.world.agents[1]

        simulation.apply_intervention(
            Intervention(
                day=1,
                kind="broadcast",
                params={
                    "intent": "repair_routes",
                    "tone": "hope",
                    "strength": 0.1,
                    "message": "Reopen blocked routes before hauling more food.",
                    "target_agent_ids": [target.id],
                },
            )
        )

        event = simulation.world.event_log[-1]
        self.assertEqual(event.kind, "broadcast")
        self.assertIn("intent repair_routes", event.description)
        self.assertEqual(event.effects["target_count"], 1.0)
        self.assertTrue(
            any(memory.kind == "broadcast" for memory in target.memory_stream)
        )
        self.assertFalse(
            any(memory.kind == "broadcast" for memory in other.memory_stream)
        )

    def test_observer_repair_intent_biases_later_plan(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.day = 1
        agent = simulation.world.agents[0]
        other = simulation.world.agents[1]
        simulation.world.resources.update(
            {"food": 100.0, "materials": 100.0, "shelter": 100.0}
        )
        simulation.world.blocked_routes["commons|north_field"] = 1.0
        agent.needs.food = 0.8
        agent.needs.energy = 0.8
        agent.needs.safety = 0.8
        agent.needs.belonging = 0.8
        agent.needs.meaning = 0.8

        simulation.apply_intervention(
            Intervention(
                day=1,
                kind="broadcast",
                params={
                    "intent": "repair_routes",
                    "tone": "neutral",
                    "strength": 0.12,
                    "message": "Please reopen the blocked north route.",
                    "target_agent_ids": [agent.id],
                },
            )
        )

        plan = RuleBasedCognition().propose_plan(agent, simulation.world)
        other_plan = RuleBasedCognition().propose_plan(other, simulation.world)

        self.assertEqual(plan.action, Action.REPAIR)
        self.assertIn("observer intent emphasizes route repair", plan.reason)
        self.assertNotIn("observer intent emphasizes route repair", other_plan.reason)

    def test_relationship_crisis_blocks_passive_repair_until_social_action(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.10
        second.relationships[first.id] = 0.12
        simulation.world.day = 5

        simulation._apply_relationship_crises()
        before = first.relationships[second.id]
        simulation._apply_social_drift()

        self.assertIn("a1|a2", simulation.world.relationship_crises)
        self.assertEqual(first.relationships[second.id], before)
        self.assertTrue(any(event.kind == "relationship_crisis" for event in simulation.world.event_log))

        first.relationships[second.id] = 0.39
        second.relationships[first.id] = 0.39
        simulation._apply_action(first, Plan(Action.SOCIALIZE, 1.0, "repair trust", target_id=second.id))

        self.assertNotIn("a1|a2", simulation.world.relationship_crises)
        self.assertTrue(any(event.kind == "reconciliation" for event in simulation.world.event_log))

    def test_observer_mediation_reconciles_ready_relationship_crisis(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        simulation.world.day = 6
        simulation.world.relationship_crises["a1|a2"] = 3
        first.relationships[second.id] = 0.39
        second.relationships[first.id] = 0.39

        simulation.apply_intervention(
            Intervention(
                day=6,
                kind="mediation",
                actor_id="The_Envoy",
                reason="observer asked for a direct repair meeting",
                params={
                    "target_agent_ids": [first.id, second.id],
                    "message": "Name the grievance and rebuild a working agreement.",
                },
            )
        )

        self.assertNotIn("a1|a2", simulation.world.relationship_crises)
        self.assertGreater(first.relationships[second.id], 0.42)
        self.assertTrue(any(event.kind == "mediation" for event in simulation.world.event_log))
        self.assertTrue(any(event.kind == "reconciliation" for event in simulation.world.event_log))
        self.assertTrue(
            any(memory.kind == "mediation" for memory in first.memory_stream)
        )

    def test_observer_mediation_requires_two_known_targets(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.day = 2

        with self.assertRaises(ValueError):
            simulation.apply_intervention(
                Intervention(
                    day=2,
                    kind="mediation",
                    params={"target_agent_ids": ["a1", "missing"]},
                )
            )

    def test_experiment_returns_report_for_each_seed(self) -> None:
        reports = run_experiment(seeds=[1, 2, 3], days=30)

        self.assertEqual([report.seed for report in reports], [1, 2, 3])
        self.assertTrue(all(report.findings for report in reports))


if __name__ == "__main__":
    unittest.main()
