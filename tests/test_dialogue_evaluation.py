import unittest

from virtual_society import Simulation
from virtual_society.dialogue_evaluation import assess_dialogue_follow_through
from virtual_society.model import MemoryItem


class DialogueEvaluationTests(unittest.TestCase):
    def test_generated_dialogue_traces_memory_reflection_plan_and_baseline_delta(self) -> None:
        simulation = Simulation(seed=7)
        baseline = Simulation(seed=7)
        world = simulation.world
        world.day = 35
        speaker = world.agents[0]
        partner = world.agents[1]
        generated = "Ari asked Bo to keep food distribution visible through the council."
        for agent in (speaker, partner):
            agent.memory_stream.append(
                MemoryItem(day=21, kind="dialogue", text=generated, importance=0.70)
            )
        speaker.reflections = [
            "day 28: Ari kept food distribution and council trust salient."
        ]
        partner.reflections = [
            "day 28: Bo treated visible food distribution as trust work."
        ]
        speaker.plan_history = [
            "day 22: haul | food distribution needs visible council work",
        ]
        partner.plan_history = [
            "day 22: socialize | council trust needs repair",
        ]
        baseline.world.day = 35
        baseline.world.agents[0].reflections = [
            "day 28: Ari reflected on routine labor."
        ]
        baseline.world.agents[1].reflections = [
            "day 28: Bo reflected on routine labor."
        ]
        baseline.world.agents[0].plan_history = [
            "day 22: haul | routine depot work",
        ]
        baseline.world.agents[1].plan_history = [
            "day 22: socialize | routine trust work",
        ]

        items = assess_dialogue_follow_through(
            world,
            [
                {
                    "day": 21,
                    "speaker_id": speaker.id,
                    "speaker_name": speaker.name,
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "status": "primary",
                    "focus": "coordination",
                    "used_dialogue": generated,
                    "baseline_dialogue": "Ari and Bo discussed routine work.",
                }
            ],
            baseline_world=baseline.world,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].signal, "baseline_reflection_context_diverged")
        self.assertEqual(len(items[0].memory_evidence), 2)
        self.assertEqual(len(items[0].reflection_evidence), 2)
        self.assertEqual(len(items[0].plan_evidence), 2)
        self.assertEqual(len(items[0].baseline_reflection_deltas), 2)
        self.assertEqual(len(items[0].baseline_plan_deltas), 2)
        self.assertIn("reflection-context differences", items[0].summary)

    def test_follow_through_ignores_failed_generated_dialogue(self) -> None:
        simulation = Simulation(seed=7)

        items = assess_dialogue_follow_through(
            simulation.world,
            [
                {
                    "day": 21,
                    "speaker_id": "a1",
                    "partner_id": "a2",
                    "status": "fallback_after_error",
                    "used_dialogue": "rule fallback",
                    "focus": "routine",
                }
            ],
        )

        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
