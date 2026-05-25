import unittest

from virtual_society import Intervention, Simulation
from virtual_society.choice_tension_evaluation import assess_choice_tensions


class ChoiceTensionEvaluationTests(unittest.TestCase):
    def test_choice_tension_links_observer_intent_and_resource_pressure(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="broadcast",
                    params={
                        "intent": "repair_routes",
                        "target_agent_ids": ["a2"],
                        "message": "Reopen blocked routes.",
                    },
                )
            ],
        )
        trace = [
            {
                "day": 1,
                "agent_id": "a2",
                "agent_name": "Bo",
                "status": "primary",
                "baseline_plan": {
                    "action": "haul",
                    "reason": "food needs hauling to shared depots",
                },
                "proposed_plan": {
                    "action": "haul",
                    "reason": (
                        "Food pressure remains urgent, but blocked routes and "
                        "repair memories still matter."
                    ),
                },
                "used_plan": {
                    "action": "haul",
                    "reason": "Food pressure remains urgent.",
                },
            }
        ]

        findings = assess_choice_tensions(simulation.world, trace)

        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0].signal,
            "choice_tension_baseline_aligned_with_tradeoff",
        )
        self.assertIn("repair_routes", findings[0].observer_intents)
        self.assertIn("logistics", findings[0].competing_groups)
        self.assertIn("repair", findings[0].competing_groups)


if __name__ == "__main__":
    unittest.main()
