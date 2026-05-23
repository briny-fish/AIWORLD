import unittest

from virtual_society.cognition_outcome_evaluation import assess_cognition_outcomes
from virtual_society.model import Metrics


class CognitionOutcomeEvaluationTests(unittest.TestCase):
    def test_outcome_links_cognition_impact_to_metric_windows(self) -> None:
        metrics = [
            _metrics(21, average_need=0.50, average_trust=0.50, food=5.0),
            _metrics(22, average_need=0.51, average_trust=0.50, food=6.0),
            _metrics(24, average_need=0.52, average_trust=0.51, food=7.0),
            _metrics(28, average_need=0.53, average_trust=0.51, food=8.0),
            _metrics(30, average_need=0.54, average_trust=0.52, food=9.0),
        ]
        baseline = [
            _metrics(21, average_need=0.49, average_trust=0.50, food=5.0),
            _metrics(22, average_need=0.50, average_trust=0.50, food=5.8),
            _metrics(24, average_need=0.51, average_trust=0.50, food=6.8),
            _metrics(28, average_need=0.52, average_trust=0.50, food=7.2),
            _metrics(30, average_need=0.52, average_trust=0.50, food=8.2),
        ]
        impacts = [
            {
                "day": 21,
                "agent_id": "a1",
                "agent_name": "Ari",
                "signal": "cognition_action_diverged",
            }
        ]

        outcomes = assess_cognition_outcomes(metrics, baseline, impacts)

        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].agent_name, "Ari")
        self.assertEqual(outcomes[0].outcome_signal, "outcome_social_gain")
        self.assertEqual(outcomes[0].windows[-1].label, "final")
        self.assertEqual(outcomes[0].windows[-1].deltas["food"], 0.8)
        self.assertIn("average_need +0.02", outcomes[0].summary)

    def test_outcome_detects_resource_gain_with_social_cost(self) -> None:
        metrics = [_metrics(30, average_need=0.51, average_trust=0.49, food=9.0)]
        baseline = [_metrics(30, average_need=0.52, average_trust=0.50, food=8.0)]
        impacts = [{"day": 30, "agent_id": "a1", "agent_name": "Ari", "signal": "x"}]

        outcomes = assess_cognition_outcomes(metrics, baseline, impacts)

        self.assertEqual(
            outcomes[0].outcome_signal,
            "mixed_resource_gain_social_cost",
        )

    def test_outcome_requires_baseline_metrics(self) -> None:
        impacts = [{"day": 1, "agent_id": "a1", "agent_name": "Ari", "signal": "x"}]

        self.assertEqual(assess_cognition_outcomes([], None, impacts), [])


def _metrics(
    day: int,
    average_need: float,
    average_trust: float,
    food: float,
    materials: float = 0.0,
    shelter: float = 0.0,
) -> Metrics:
    return Metrics(
        day=day,
        population=12,
        food=food,
        materials=materials,
        shelter=shelter,
        average_need=average_need,
        average_trust=average_trust,
        average_reputation=0.5,
        institutional_cohesion=0.5,
        crisis_events=0,
    )


if __name__ == "__main__":
    unittest.main()
