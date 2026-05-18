import unittest

from virtual_society import Simulation
from virtual_society.generative_memory import retrieve_memories
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


class GenerativeMemoryTests(unittest.TestCase):
    def test_events_create_structured_agent_memories(self) -> None:
        simulation = Simulation(seed=7)

        simulation.run(1)
        agent = simulation.world.agents[0]

        self.assertTrue(agent.memories)
        self.assertTrue(agent.memory_stream)
        self.assertGreater(agent.memory_stream[-1].importance, 0)
        self.assertIn(agent.memory_stream[-1].kind, {"work", "rest", "social", "dialogue", "transport"})

    def test_memory_retrieval_prioritizes_query_relevant_items(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(8)
        agent = simulation.world.agents[0]

        memories = retrieve_memories(
            agent,
            query="food hunger rationing repair",
            current_day=simulation.world.day,
            limit=4,
        )

        self.assertLessEqual(len(memories), 4)
        self.assertTrue(memories)
        self.assertTrue(all(memory.text for memory in memories))

    def test_weekly_reflection_is_recorded(self) -> None:
        simulation = Simulation(seed=7)

        simulation.run(7)

        self.assertTrue(all(agent.reflections for agent in simulation.world.agents))
        self.assertTrue(any(event.kind == "reflection" for event in simulation.world.event_log))

    def test_social_action_records_dialogue_for_both_participants(self) -> None:
        simulation = Simulation(seed=7, cognition=SocialCognition())

        simulation.run(1)

        dialogue_events = [
            event
            for event in simulation.world.event_log
            if event.kind == "dialogue"
        ]
        self.assertTrue(dialogue_events)
        first_dialogue = dialogue_events[0]
        participants = [
            agent
            for agent in simulation.world.agents
            if first_dialogue.description in [memory.text for memory in agent.memory_stream]
        ]
        self.assertGreaterEqual(len(participants), 2)


if __name__ == "__main__":
    unittest.main()
