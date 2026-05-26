import unittest

from virtual_society import Simulation
from virtual_society.reflection_contract import (
    ReflectionParseError,
    build_reflection_context,
    parse_reflection_response,
    render_reflection_prompt,
)


class ReflectionContractTests(unittest.TestCase):
    def test_context_grounds_reflection_in_profile_memories_and_baseline(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(3)
        agent = simulation.world.agents[0]

        context = build_reflection_context(
            agent,
            simulation.world,
            current_day=simulation.world.day,
            lookback_days=3,
            baseline_reflection="Ari noticed the week stayed stable.",
        )
        prompt = render_reflection_prompt(context)

        self.assertEqual(context.agent["id"], agent.id)
        self.assertIn("profile", context.agent)
        self.assertIn("recent_life_journal", context.agent)
        self.assertTrue(context.agent["recent_life_journal"])
        self.assertTrue(context.recent_memories)
        self.assertEqual(context.baseline_reflection, "Ari noticed the week stayed stable.")
        self.assertIn("memory_refs", prompt)
        self.assertIn("baseline_reflection", prompt)
        self.assertIn("recent_life_journal", prompt)

    def test_parse_reflection_response_accepts_memory_grounded_summary(self) -> None:
        proposal = parse_reflection_response(
            {
                "summary": "Ari saw field work and food pressure as the same duty.",
                "focus": "work",
                "memory_refs": [0, 1, 1],
            },
            memory_count=2,
        )

        self.assertEqual(proposal.focus, "work")
        self.assertEqual(proposal.memory_refs, [0, 1])

    def test_parse_reflection_response_requires_refs_when_memories_exist(self) -> None:
        with self.assertRaises(ReflectionParseError):
            parse_reflection_response(
                {
                    "summary": "Ari took stock of the week.",
                    "focus": "routine",
                    "memory_refs": [],
                },
                memory_count=1,
            )

    def test_parse_reflection_response_rejects_unknown_refs(self) -> None:
        with self.assertRaises(ReflectionParseError):
            parse_reflection_response(
                {
                    "summary": "Ari remembered something unavailable.",
                    "focus": "identity",
                    "memory_refs": [2],
                },
                memory_count=2,
            )


if __name__ == "__main__":
    unittest.main()
