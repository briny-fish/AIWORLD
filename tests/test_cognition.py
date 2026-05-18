import unittest

from virtual_society.cognition import RuleBasedCognition
from virtual_society.model import Action
from virtual_society import Simulation


class CognitionTests(unittest.TestCase):
    def test_rule_based_cognition_prioritizes_food_scarcity(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        simulation.world.resources["food"] = 0.0
        agent.needs.food = 0.3

        plan = RuleBasedCognition().propose_plan(agent, simulation.world)

        self.assertEqual(plan.action, Action.FARM)
        self.assertIn("food", plan.reason)

    def test_rule_based_cognition_selects_social_target(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        agent.needs.food = 1.0
        agent.needs.energy = 1.0
        agent.needs.safety = 1.0
        agent.needs.belonging = 0.1
        simulation.world.resources["food"] = 100.0
        weakest = min(agent.relationships, key=lambda other_id: agent.relationships[other_id])

        plan = RuleBasedCognition().propose_plan(agent, simulation.world)

        self.assertEqual(plan.action, Action.SOCIALIZE)
        self.assertEqual(plan.target_id, weakest)

    def test_simulation_records_plan_history(self) -> None:
        simulation = Simulation(seed=7)

        simulation.run(3)

        self.assertTrue(all(agent.active_plan is not None for agent in simulation.world.agents))
        self.assertTrue(all(agent.plan_history for agent in simulation.world.agents))
        self.assertTrue(any(event.kind == "plan" for event in simulation.world.event_log))

    def test_blocked_repair_plan_falls_back_to_gather(self) -> None:
        simulation = Simulation(seed=7)
        for agent in simulation.world.agents:
            agent.needs.safety = 0.1
            agent.needs.food = 1.0
            agent.needs.energy = 1.0
        for location in simulation.world.locations:
            location.resources["food"] = 0.0
            location.resources["materials"] = 0.0
            location.resources["shelter"] = 0.0
        simulation.world.locations[0].resources["food"] = 100.0
        simulation._sync_world_resources()

        simulation.run(1)

        self.assertTrue(any(event.kind == "plan_blocked" for event in simulation.world.event_log))
        self.assertTrue(
            any("gathering materials first" in agent.active_plan.reason for agent in simulation.world.agents)
        )


if __name__ == "__main__":
    unittest.main()
