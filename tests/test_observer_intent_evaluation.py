import unittest

from virtual_society import Simulation
from virtual_society.interventions import Intervention
from virtual_society.observer_intent_evaluation import assess_observer_intents


class ObserverIntentEvaluationTests(unittest.TestCase):
    def test_observer_intent_links_memory_and_later_plan(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.day = 1
        agent = simulation.world.agents[0]
        simulation.apply_intervention(
            Intervention(
                day=1,
                kind="broadcast",
                params={
                    "intent": "repair_routes",
                    "tone": "hope",
                    "strength": 0.1,
                    "target_agent_ids": [agent.id],
                    "message": "Reopen blocked routes.",
                },
            )
        )
        agent.plan_history.append(
            "day 1: repair | observer intent emphasizes route repair"
        )

        findings = assess_observer_intents(simulation.world)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].intent, "repair_routes")
        self.assertEqual(findings[0].signal, "intent_memory_plan_echo")
        self.assertEqual(findings[0].expected_targets, 1)
        self.assertEqual(findings[0].memory_hits, 1)
        self.assertEqual(findings[0].plan_hits, 1)


if __name__ == "__main__":
    unittest.main()
