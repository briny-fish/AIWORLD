import unittest

from virtual_society import Simulation
from virtual_society.cognition_impact_evaluation import assess_cognition_impacts
from virtual_society.model import Event


class CognitionImpactEvaluationTests(unittest.TestCase):
    def test_accepted_cognition_action_divergence_records_execution_and_plan_delta(self) -> None:
        simulation = Simulation(seed=7)
        baseline = Simulation(seed=7)
        world = simulation.world
        world.day = 30
        baseline.world.day = 30
        agent = world.agents[0]
        baseline_agent = baseline.world.agents[0]
        agent.plan_history = [
            "day 21: rest | generated recovery protects later shared work",
            "day 22: farm | resumed food work",
        ]
        baseline_agent.plan_history = [
            "day 21: farm | shared food stores are low",
            "day 22: farm | shared food stores are low",
        ]
        world.event_log.append(
            Event(
                day=21,
                kind="rest",
                actor_id=agent.id,
                description="Ari rested.",
                effects={"energy": 0.32},
            )
        )

        impacts = assess_cognition_impacts(
            world,
            [
                {
                    "day": 21,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "status": "primary",
                    "baseline_plan": {
                        "action": "farm",
                        "reason": "shared food stores are low",
                        "target_id": None,
                        "horizon_days": 1,
                    },
                    "proposed_plan": {
                        "action": "rest",
                        "reason": "generated recovery protects later shared work",
                        "target_id": None,
                        "horizon_days": 1,
                    },
                    "used_plan": {
                        "action": "rest",
                        "reason": "generated recovery protects later shared work",
                        "target_id": None,
                        "horizon_days": 1,
                    },
                }
            ],
            baseline_world=baseline.world,
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].signal, "cognition_action_diverged")
        self.assertEqual(len(impacts[0].execution_evidence), 1)
        self.assertEqual(impacts[0].baseline_plan_deltas[0].change_kind, "action")
        self.assertIn("baseline=farm", impacts[0].summary)

    def test_policy_blocked_proposal_is_not_counted_as_action_divergence(self) -> None:
        simulation = Simulation(seed=7)
        world = simulation.world
        world.day = 21
        agent = world.agents[0]

        impacts = assess_cognition_impacts(
            world,
            [
                {
                    "day": 21,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "status": "baseline_after_policy",
                    "baseline_plan": {
                        "action": "farm",
                        "reason": "shared food stores are low",
                        "target_id": None,
                        "horizon_days": 1,
                    },
                    "proposed_plan": {
                        "action": "rest",
                        "reason": "generated recovery",
                        "target_id": None,
                        "horizon_days": 1,
                    },
                    "used_plan": {
                        "action": "farm",
                        "reason": "shared food stores are low",
                        "target_id": None,
                        "horizon_days": 1,
                    },
                }
            ],
        )

        self.assertEqual(impacts[0].signal, "cognition_proposal_policy_blocked")
        self.assertFalse(impacts[0].used_diverged_from_baseline)
        self.assertTrue(impacts[0].proposed_diverged_from_baseline)


if __name__ == "__main__":
    unittest.main()
