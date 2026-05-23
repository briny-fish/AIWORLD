import unittest

from virtual_society import Simulation
from virtual_society.generative_chain_evaluation import assess_generated_chains
from virtual_society.model import MemoryItem


class GenerativeChainEvaluationTests(unittest.TestCase):
    def test_generated_dialogue_can_link_to_generated_reflection_and_plan_delta(self) -> None:
        simulation = Simulation(seed=7)
        baseline = Simulation(seed=7)
        world = simulation.world
        world.day = 35
        agent = world.agents[0]
        partner = world.agents[1]
        dialogue = "Ari asked Bo to keep food distribution visible through the council."
        reflection = "Ari treated food distribution and council trust as the week priority."
        agent.memory_stream.append(
            MemoryItem(day=21, kind="dialogue", text=dialogue, importance=0.70)
        )
        agent.plan_history = [
            "day 29: farm | food distribution remains urgent",
        ]
        baseline.world.day = 35
        baseline.world.agents[0].plan_history = [
            "day 29: gather | materials are depleted",
        ]

        chains = assess_generated_chains(
            world,
            [
                {
                    "day": 21,
                    "speaker_id": agent.id,
                    "speaker_name": agent.name,
                    "partner_id": partner.id,
                    "partner_name": partner.name,
                    "status": "primary",
                    "focus": "coordination",
                    "used_dialogue": dialogue,
                }
            ],
            [
                {
                    "day": 28,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "status": "primary",
                    "focus": "scarcity",
                    "used_reflection": reflection,
                }
            ],
            baseline_world=baseline.world,
        )

        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].signal, "generated_chain_action_diverged")
        self.assertIn("food", chains[0].shared_terms)
        self.assertEqual(len(chains[0].memory_evidence), 1)
        self.assertEqual(len(chains[0].plan_evidence), 1)
        self.assertEqual(chains[0].baseline_plan_deltas[0].change_kind, "action")

    def test_generated_chain_requires_accepted_dialogue_and_reflection(self) -> None:
        simulation = Simulation(seed=7)

        chains = assess_generated_chains(
            simulation.world,
            [
                {
                    "day": 21,
                    "speaker_id": "a1",
                    "partner_id": "a2",
                    "status": "fallback_after_error",
                    "used_dialogue": "fallback",
                }
            ],
            [
                {
                    "day": 28,
                    "agent_id": "a1",
                    "status": "primary",
                    "used_reflection": "generated reflection",
                }
            ],
        )

        self.assertEqual(chains, [])

    def test_shared_terms_must_come_from_generated_text(self) -> None:
        simulation = Simulation(seed=7)
        world = simulation.world
        world.day = 35
        agent = world.agents[0]
        partner = world.agents[1]
        dialogue = "Rook promised roof repairs at west hall."
        reflection = "Morgan weighed council trust for route warnings."
        agent.memory_stream.append(
            MemoryItem(day=21, kind="dialogue", text=dialogue, importance=0.70)
        )
        agent.plan_history = [
            "day 29: repair | route warnings remain important",
        ]

        chains = assess_generated_chains(
            world,
            [
                {
                    "day": 21,
                    "speaker_id": agent.id,
                    "partner_id": partner.id,
                    "status": "primary",
                    "focus": "coordination",
                    "used_dialogue": dialogue,
                }
            ],
            [
                {
                    "day": 28,
                    "agent_id": agent.id,
                    "status": "primary",
                    "focus": "coordination",
                    "used_reflection": reflection,
                }
            ],
        )

        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].shared_terms, [])
        self.assertEqual(chains[0].signal, "weak_generated_chain")

    def test_participant_names_do_not_create_shared_terms(self) -> None:
        simulation = Simulation(seed=7)
        world = simulation.world
        world.day = 35
        agent = world.agents[0]
        partner = world.agents[1]
        dialogue = "Ari repaired the roof."
        reflection = "Ari weighed council trust."
        agent.memory_stream.append(
            MemoryItem(day=21, kind="dialogue", text=dialogue, importance=0.70)
        )

        chains = assess_generated_chains(
            world,
            [
                {
                    "day": 21,
                    "speaker_id": agent.id,
                    "partner_id": partner.id,
                    "status": "primary",
                    "focus": "routine",
                    "used_dialogue": dialogue,
                }
            ],
            [
                {
                    "day": 28,
                    "agent_id": agent.id,
                    "status": "primary",
                    "focus": "coordination",
                    "used_reflection": reflection,
                }
            ],
        )

        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].shared_terms, [])
        self.assertEqual(chains[0].signal, "weak_generated_chain")


if __name__ == "__main__":
    unittest.main()
