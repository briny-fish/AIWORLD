import unittest

from virtual_society import (
    AGENT_DOSSIER_VERSION,
    Simulation,
    build_agent_dossier,
    build_agent_dossiers,
    build_agent_record,
    build_relationship_links,
)


class AgentDossierTests(unittest.TestCase):
    def test_agent_dossier_exposes_identity_continuity_and_affordances(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(3)
        simulation.world.relationship_crises["a1|a2"] = 1

        dossier = build_agent_dossier(simulation.world, "a1", seed=7)

        self.assertEqual(dossier["kind"], "agent_dossier")
        self.assertEqual(dossier["version"], AGENT_DOSSIER_VERSION)
        self.assertEqual(dossier["agent"]["id"], "a1")
        self.assertTrue(dossier["agent"]["recent_life_journal"])
        self.assertTrue(dossier["continuity"]["identity"]["long_term_goals"])
        self.assertTrue(dossier["continuity"]["latest_life_episode"])
        self.assertTrue(dossier["continuity"]["latest_memory"])
        self.assertIn("social_history", dossier)
        self.assertIn("influence_chains", dossier)
        self.assertEqual(
            dossier["continuity"]["social_state"]["relationship_crisis_count"],
            1,
        )

        affordance_ids = {
            item["id"]
            for item in dossier["observer_affordances"]
        }
        self.assertIn("broadcast_intent", affordance_ids)
        self.assertIn("mediate_crisis", affordance_ids)
        self.assertIn("support_location_food", affordance_ids)

    def test_agent_dossier_index_uses_shared_contract(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(1)

        index = build_agent_dossiers(simulation.world, seed=7)

        self.assertEqual(index["kind"], "agent_dossier_index")
        self.assertEqual(index["version"], AGENT_DOSSIER_VERSION)
        self.assertEqual(index["day"], 1)
        self.assertEqual(len(index["agents"]), len(simulation.world.agents))
        self.assertEqual(index["agents"][0]["version"], AGENT_DOSSIER_VERSION)

    def test_agent_record_and_relationship_links_are_stable(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(1)
        agent = simulation.world.agents[0]

        record = build_agent_record(agent)
        links = build_relationship_links(simulation.world)

        self.assertIn("skills", record)
        self.assertIn("active_plan", record)
        self.assertTrue(links)
        self.assertEqual(
            len({item["pair"] for item in links}),
            len(links),
        )


if __name__ == "__main__":
    unittest.main()
