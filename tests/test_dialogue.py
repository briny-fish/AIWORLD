import unittest

from virtual_society import Simulation
from virtual_society.dialogue import HybridDialogue, HybridDialogueConfig, RuleBasedDialogue
from virtual_society.dialogue_contract import DialogueProposal
from virtual_society.model import Action, Plan


class SocialCognition:
    def propose_plan(self, agent, world):
        target_id = next(other.id for other in world.agents if other.id != agent.id)
        return Plan(
            action=Action.SOCIALIZE,
            priority=1.0,
            reason="test social dialogue",
            target_id=target_id,
        )


class FixedDialogue:
    def __init__(self) -> None:
        self.calls = 0

    def propose_dialogue(self, speaker, partner, world, baseline_dialogue):
        self.calls += 1
        return DialogueProposal(
            text=f"{speaker.name} asked {partner.name} to coordinate food work.",
            focus="coordination",
            memory_refs=[0],
        )


class FailingDialogue:
    def __init__(self) -> None:
        self.calls = 0

    def propose_dialogue(self, speaker, partner, world, baseline_dialogue):
        self.calls += 1
        raise RuntimeError("dialogue provider failed")


class HybridDialogueTests(unittest.TestCase):
    def test_uses_primary_only_for_selected_speaker(self) -> None:
        primary = FixedDialogue()
        hybrid = HybridDialogue(
            primary=primary,
            fallback=RuleBasedDialogue(),
            config=HybridDialogueConfig(agent_ids={"a1"}, max_calls=1),
        )
        simulation = Simulation(seed=7, cognition=SocialCognition(), dialogue=hybrid)

        simulation.run(1)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(hybrid.stats.llm_successes, 1)
        self.assertGreater(hybrid.stats.skipped_calls, 0)
        self.assertEqual(hybrid.trace[0].speaker_id, "a1")
        self.assertEqual(hybrid.trace[0].status, "primary")
        self.assertEqual(hybrid.trace[0].focus, "coordination")

    def test_falls_back_after_primary_failure(self) -> None:
        primary = FailingDialogue()
        hybrid = HybridDialogue(
            primary=primary,
            fallback=RuleBasedDialogue(),
            config=HybridDialogueConfig(agent_ids={"a1"}, max_calls=2, max_failures=1),
        )
        simulation = Simulation(seed=7, cognition=SocialCognition(), dialogue=hybrid)

        simulation.run(1)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(hybrid.stats.llm_failures, 1)
        self.assertEqual(hybrid.trace[0].status, "fallback_after_error")
        self.assertIsNone(hybrid.trace[0].proposed_dialogue)
        self.assertIn("dialogue provider failed", hybrid.trace[0].error or "")


if __name__ == "__main__":
    unittest.main()
