import unittest

from virtual_society import Simulation
from virtual_society.dialogue_contract import (
    DialogueParseError,
    build_dialogue_context,
    parse_dialogue_response,
    render_dialogue_prompt,
)


class DialogueContractTests(unittest.TestCase):
    def test_context_contains_profiles_trust_memories_and_baseline(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(2)
        speaker = simulation.world.agents[0]
        partner = simulation.world.agents[1]

        context = build_dialogue_context(
            speaker,
            partner,
            simulation.world,
            baseline_dialogue="Ari and Bo discussed routine work.",
        )
        prompt = render_dialogue_prompt(context)

        self.assertEqual(context.speaker["id"], speaker.id)
        self.assertEqual(context.partner["id"], partner.id)
        self.assertTrue(context.speaker["recent_life_journal"])
        self.assertTrue(context.partner["recent_life_journal"])
        self.assertIn("average_trust", context.relationship)
        self.assertTrue(context.recent_memories)
        self.assertIn("baseline_dialogue", prompt)
        self.assertIn("memory_refs", prompt)
        self.assertIn("life_journal", prompt)

    def test_parse_dialogue_response_accepts_grounded_output(self) -> None:
        proposal = parse_dialogue_response(
            {
                "text": "Ari asked Bo to keep food distribution visible.",
                "focus": "coordination",
                "memory_refs": [0, 1, 1],
            },
            memory_count=2,
        )

        self.assertEqual(proposal.focus, "coordination")
        self.assertEqual(proposal.memory_refs, [0, 1])

    def test_parse_dialogue_response_requires_refs_when_memories_exist(self) -> None:
        with self.assertRaises(DialogueParseError):
            parse_dialogue_response(
                {
                    "text": "Ari and Bo talked.",
                    "focus": "routine",
                    "memory_refs": [],
                },
                memory_count=1,
            )


if __name__ == "__main__":
    unittest.main()
