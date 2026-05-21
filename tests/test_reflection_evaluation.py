import unittest

from virtual_society import Simulation
from virtual_society.model import Event
from virtual_society.reflection_evaluation import assess_reflection_follow_through


class ReflectionEvaluationTests(unittest.TestCase):
    def test_generated_reflection_traces_later_behavior_and_baseline_delta(self) -> None:
        simulation = Simulation(seed=7)
        baseline = Simulation(seed=7)
        world = simulation.world
        world.day = 23
        agent = world.agents[0]
        agent.plan_history = [
            "day 22: farm | food security remains urgent",
            "day 23: haul | food needs distribution",
        ]
        world.event_log.append(
            Event(
                day=23,
                kind="dialogue",
                actor_id=agent.id,
                description="Ari and Bo discussed food distribution and trust.",
            )
        )
        baseline.world.day = 23
        baseline.world.agents[0].plan_history = [
            "day 22: gather | materials are depleted",
            "day 23: gather | materials are depleted",
        ]
        trace = [
            {
                "day": 21,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "status": "primary",
                "used_reflection": "Ari should keep food security and hauling salient.",
                "focus": "scarcity",
            }
        ]

        items = assess_reflection_follow_through(
            world,
            trace,
            baseline_world=baseline.world,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].signal, "baseline_action_diverged")
        self.assertEqual(len(items[0].plan_evidence), 2)
        self.assertEqual(len(items[0].dialogue_evidence), 1)
        self.assertEqual(len(items[0].baseline_plan_deltas), 2)
        self.assertTrue(
            all(delta.change_kind == "action" for delta in items[0].baseline_plan_deltas)
        )
        self.assertIn("against the rule baseline", items[0].summary)

    def test_reason_only_baseline_delta_is_plan_context_signal(self) -> None:
        simulation = Simulation(seed=7)
        baseline = Simulation(seed=7)
        world = simulation.world
        world.day = 23
        world.agents[0].plan_history = [
            "day 22: haul | reflection keeps logistics salient",
        ]
        baseline.world.day = 23
        baseline.world.agents[0].plan_history = [
            "day 22: haul | routine depot work",
        ]

        items = assess_reflection_follow_through(
            world,
            [
                {
                    "day": 21,
                    "agent_id": "a1",
                    "status": "primary",
                    "used_reflection": "Ari keeps hauling and routes salient.",
                    "focus": "work",
                }
            ],
            baseline_world=baseline.world,
        )

        self.assertEqual(items[0].signal, "baseline_plan_context_diverged")
        self.assertEqual(items[0].baseline_plan_deltas[0].change_kind, "context")
        self.assertIn("same recorded actions", items[0].summary)

    def test_follow_through_ignores_failed_generated_reflections(self) -> None:
        simulation = Simulation(seed=7)

        items = assess_reflection_follow_through(
            simulation.world,
            [
                {
                    "day": 7,
                    "agent_id": "a1",
                    "status": "fallback_after_error",
                    "used_reflection": "rule fallback",
                    "focus": "routine",
                }
            ],
        )

        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
