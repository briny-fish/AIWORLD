import unittest

from virtual_society.counterfactual_evaluation import assess_counterfactual_trace


class CounterfactualEvaluationTests(unittest.TestCase):
    def test_empty_trace_returns_empty_assessment(self) -> None:
        assessment = assess_counterfactual_trace([]).as_dict()

        self.assertEqual(assessment["total"], 0)
        self.assertEqual(assessment["accepted"], 0)
        self.assertEqual(assessment["rejected"], 0)
        self.assertEqual(assessment["by_agent"], [])
        self.assertEqual(assessment["by_action_pair"], [])
        self.assertIn("No counterfactual", assessment["summary"])

    def test_trace_aggregates_probes_by_agent_and_action_pair(self) -> None:
        trace = [
            {
                "day": 21,
                "agent_id": "a1",
                "agent_name": "Ari",
                "status": "primary",
                "counterfactual": {
                    "baseline": {"action": "farm", "score": 4.9},
                    "proposed": {"action": "rest", "score": 5.0},
                    "score_delta": 0.1,
                    "recommendation": "proposed",
                },
            },
            {
                "day": 28,
                "agent_id": "a2",
                "agent_name": "Bo",
                "status": "baseline_after_counterfactual",
                "counterfactual": {
                    "baseline": {"action": "repair", "score": 5.2},
                    "proposed": {"action": "rest", "score": 5.1},
                    "score_delta": -0.1,
                    "recommendation": "baseline",
                },
            },
        ]

        assessment = assess_counterfactual_trace(trace).as_dict()

        self.assertEqual(assessment["total"], 2)
        self.assertEqual(assessment["accepted"], 1)
        self.assertEqual(assessment["rejected"], 1)
        self.assertEqual(assessment["acceptance_rate"], 0.5)
        self.assertEqual(assessment["average_score_delta"], 0.0)
        self.assertEqual(assessment["worst_score_delta"], -0.1)
        self.assertEqual(assessment["best_score_delta"], 0.1)
        self.assertEqual(assessment["worst_record"]["agent_name"], "Bo")
        self.assertEqual(assessment["worst_record"]["baseline_action"], "repair")
        agents = {item["label"]: item for item in assessment["by_agent"]}
        action_pairs = {item["label"]: item for item in assessment["by_action_pair"]}
        self.assertEqual(agents["Ari"]["accepted"], 1)
        self.assertEqual(agents["Bo"]["rejected"], 1)
        self.assertEqual(action_pairs["farm -> rest"]["accepted"], 1)
        self.assertEqual(action_pairs["repair -> rest"]["rejected"], 1)
        self.assertIn("accepted 1/2", assessment["summary"])


if __name__ == "__main__":
    unittest.main()
