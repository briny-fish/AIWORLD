import unittest

from virtual_society import Simulation
from virtual_society.social_evaluation import assess_social_dynamics


class SocialEvaluationTests(unittest.TestCase):
    def test_generative_alpha_has_twelve_agents_and_social_loop(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")

        simulation.run(30)
        findings = assess_social_dynamics(simulation.world)

        self.assertEqual(simulation.world.population, 12)
        self.assertTrue(all(agent.memory_stream for agent in simulation.world.agents))
        self.assertTrue(all(agent.reflections for agent in simulation.world.agents))
        self.assertTrue(any(event.kind == "dialogue" for event in simulation.world.event_log))
        self.assertTrue(any(finding.code == "social_loop_active" for finding in findings))


if __name__ == "__main__":
    unittest.main()
