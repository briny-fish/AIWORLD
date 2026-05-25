import unittest

from virtual_society.reason_richness_evaluation import assess_reason_richness


class ReasonRichnessEvaluationTests(unittest.TestCase):
    def test_generated_reason_can_be_richer_without_action_divergence(self) -> None:
        findings = assess_reason_richness(
            [
                {
                    "day": 8,
                    "agent_id": "a11",
                    "agent_name": "Kira",
                    "status": "primary",
                    "prompt_version": "test-prompt",
                    "baseline_plan": {
                        "action": "haul",
                        "reason": "food needs hauling to shared depots",
                    },
                    "proposed_plan": {
                        "action": "haul",
                        "reason": (
                            "Kira remembered the observer intent and weighed "
                            "council trust against food logistics before keeping "
                            "the hauling plan."
                        ),
                    },
                    "used_plan": {
                        "action": "haul",
                        "reason": "same",
                    },
                }
            ]
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].signal, "reason_richness_generated_richer")
        self.assertIn("observer_intent", findings[0].generated_groups)
        self.assertIn("relationship", findings[0].generated_groups)
        self.assertEqual(findings[0].prompt_version, "test-prompt")

    def test_target_change_is_behavior_delta(self) -> None:
        findings = assess_reason_richness(
            [
                {
                    "day": 8,
                    "agent_id": "a11",
                    "agent_name": "Kira",
                    "status": "primary",
                    "baseline_plan": {
                        "action": "socialize",
                        "target_id": "a3",
                        "reason": "relationship repair",
                    },
                    "proposed_plan": {
                        "action": "socialize",
                        "target_id": "a10",
                        "reason": (
                            "As organizer, Kira remembered observer intent, "
                            "active trust crisis, council cohesion pressure, "
                            "and chose Jules as the specific target."
                        ),
                    },
                    "used_plan": {
                        "action": "socialize",
                        "target_id": "a10",
                        "reason": "same",
                    },
                }
            ]
        )

        self.assertEqual(
            findings[0].signal,
            "reason_richness_richer_with_behavior_delta",
        )
        self.assertTrue(findings[0].target_changed)


if __name__ == "__main__":
    unittest.main()
