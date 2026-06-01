import unittest

from virtual_society import (
    SOCIAL_TIMELINE_VERSION,
    Simulation,
    build_agent_social_history,
    build_influence_chains,
    build_social_feed,
)
from virtual_society.model import Event, MemoryItem


class SocialTimelineTests(unittest.TestCase):
    def test_social_feed_marks_generated_dialogue_and_participants(self) -> None:
        simulation, trace = _simulation_with_dialogue_chain()

        feed = build_social_feed(simulation.world, dialogue_trace=trace)

        self.assertEqual(feed["kind"], "social_feed")
        self.assertEqual(feed["version"], SOCIAL_TIMELINE_VERSION)
        self.assertEqual(feed["entries"][0]["source"], "generated_llm_or_cache")
        self.assertEqual(feed["entries"][0]["focus"], "coordination")
        self.assertTrue(feed["entries"][0]["memory_grounded"])
        self.assertIn("a1", feed["entries"][0]["participant_ids"])
        self.assertIn("a2", feed["entries"][0]["participant_ids"])

    def test_agent_social_history_and_influence_chains_are_readable(self) -> None:
        simulation, trace = _simulation_with_dialogue_chain()

        history = build_agent_social_history(
            simulation.world,
            "a1",
            dialogue_trace=trace,
        )
        chains = build_influence_chains(simulation.world, agent_id="a1")

        self.assertEqual(history["kind"], "agent_social_history")
        self.assertTrue(history["entries"])
        self.assertTrue(history["influence_chains"])
        self.assertEqual(chains["version"], SOCIAL_TIMELINE_VERSION)
        self.assertTrue(chains["chains"])
        self.assertEqual(
            chains["chains"][-1]["signal"],
            "social_memory_reflection_plan_echo",
        )
        self.assertIn("later plan echo", chains["chains"][-1]["summary"])


def _simulation_with_dialogue_chain() -> tuple[Simulation, list[dict]]:
    simulation = Simulation(seed=7, world_preset="generative_alpha")
    world = simulation.world
    world.day = 3
    speaker = world.agents[0]
    partner = world.agents[1]
    text = f"{speaker.name} asked {partner.name} to keep food trust visible."
    event = Event(
        day=1,
        kind="dialogue",
        actor_id=speaker.id,
        description=text,
        effects={"trust": 0.035},
    )
    world.event_log.append(event)
    for agent, other in [(speaker, partner), (partner, speaker)]:
        agent.memory_stream.append(
            MemoryItem(
                day=1,
                kind="dialogue",
                text=text,
                importance=0.72,
                tags=["dialogue", "food", "trust"],
                actor_id=speaker.id,
                related_agent_ids=[other.id],
                location_id=agent.location_id,
            )
        )
    speaker.reflections.append(
        "day 2: Ari kept food trust visible after the conversation."
    )
    speaker.plan_history.append(
        "day 3: farm | food trust visible after Bo conversation"
    )
    trace = [
        {
            "day": 1,
            "speaker_id": speaker.id,
            "speaker_name": speaker.name,
            "partner_id": partner.id,
            "partner_name": partner.name,
            "status": "primary",
            "baseline_dialogue": f"{speaker.name} and {partner.name} discussed routine work.",
            "proposed_dialogue": text,
            "used_dialogue": text,
            "focus": "coordination",
            "memory_refs": [0],
            "error": None,
        }
    ]
    return simulation, trace


if __name__ == "__main__":
    unittest.main()

