import unittest

from virtual_society import Simulation
from virtual_society.counterfactual_cognition import compare_plan_counterfactuals
from virtual_society.model import Action, Plan


class CounterfactualCognitionTests(unittest.TestCase):
    def test_rejects_resource_damaging_rest_under_food_pressure(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        world = simulation.world
        world.day = 21
        world.resources["food"] = 0.0
        for location in world.locations:
            location.resources["food"] = 0.0
        agent = world.agents[0]
        agent.needs.food = 0.8
        agent.needs.energy = 0.9

        comparison = compare_plan_counterfactuals(
            world,
            agent.id,
            Plan(Action.FARM, 0.9, "shared food pressure"),
            Plan(Action.REST, 0.9, "recover first"),
            horizon_days=3,
            reject_threshold=0.02,
        )

        self.assertEqual(comparison.recommendation, "baseline")
        self.assertLess(comparison.score_delta, -0.02)
        self.assertGreater(
            comparison.baseline.metrics["food"],
            comparison.proposed.metrics["food"],
        )

    def test_accepts_social_plan_when_short_probe_scores_higher(self) -> None:
        simulation = Simulation(seed=7)
        world = simulation.world
        world.day = 5
        agent = world.agents[0]
        agent.needs.belonging = 0.1
        for other_id in agent.relationships:
            agent.relationships[other_id] = 0.1

        comparison = compare_plan_counterfactuals(
            world,
            agent.id,
            Plan(Action.GATHER, 0.5, "routine materials"),
            Plan(Action.SOCIALIZE, 0.9, "repair trust", target_id="a2"),
            horizon_days=2,
            reject_threshold=0.02,
        )

        self.assertEqual(comparison.recommendation, "proposed")
        self.assertGreater(comparison.score_delta, 0)
        self.assertEqual(comparison.proposed.action, "socialize")

    def test_probe_does_not_mutate_original_world(self) -> None:
        simulation = Simulation(seed=7)
        world = simulation.world
        agent = world.agents[0]
        original_day = world.day
        original_food = world.resources["food"]
        original_history = list(agent.plan_history)

        compare_plan_counterfactuals(
            world,
            agent.id,
            Plan(Action.FARM, 0.9, "farm"),
            Plan(Action.REST, 0.9, "rest"),
            horizon_days=1,
        )

        self.assertEqual(world.day, original_day)
        self.assertEqual(world.resources["food"], original_food)
        self.assertEqual(agent.plan_history, original_history)


if __name__ == "__main__":
    unittest.main()
