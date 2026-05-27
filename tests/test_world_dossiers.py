import unittest

from virtual_society import (
    WORLD_OBJECT_DOSSIER_VERSION,
    Simulation,
    build_location_dossier,
    build_location_dossiers,
    build_organization_dossier,
    build_organization_dossiers,
)


class WorldDossierTests(unittest.TestCase):
    def test_location_dossier_exposes_routes_residents_and_affordances(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.world.blocked_routes["commons|north_field"] = 0.75
        simulation.run(1)

        dossier = build_location_dossier(simulation.world, "commons", seed=7)

        self.assertEqual(dossier["kind"], "location_dossier")
        self.assertEqual(dossier["version"], WORLD_OBJECT_DOSSIER_VERSION)
        self.assertEqual(dossier["location"]["id"], "commons")
        self.assertIn("connected_routes", dossier["continuity"])
        self.assertTrue(dossier["continuity"]["residents"])
        self.assertTrue(dossier["observer_affordances"])
        self.assertIn(
            "focus_repair_here",
            {item["id"] for item in dossier["observer_affordances"]},
        )

    def test_organization_dossier_exposes_members_and_affordances(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(1)

        dossier = build_organization_dossier(
            simulation.world,
            "common_council",
            seed=7,
        )

        self.assertEqual(dossier["kind"], "organization_dossier")
        self.assertEqual(dossier["version"], WORLD_OBJECT_DOSSIER_VERSION)
        self.assertEqual(dossier["organization"]["id"], "common_council")
        self.assertTrue(dossier["continuity"]["members"])
        self.assertIn("inventory_gaps", dossier["continuity"])
        self.assertIn(
            "coordinate_members",
            {item["id"] for item in dossier["observer_affordances"]},
        )

    def test_world_object_indexes_use_shared_contract(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")

        locations = build_location_dossiers(simulation.world, seed=7)
        organizations = build_organization_dossiers(simulation.world, seed=7)

        self.assertEqual(locations["kind"], "location_dossier_index")
        self.assertEqual(locations["version"], WORLD_OBJECT_DOSSIER_VERSION)
        self.assertTrue(locations["locations"])
        self.assertEqual(organizations["kind"], "organization_dossier_index")
        self.assertEqual(organizations["version"], WORLD_OBJECT_DOSSIER_VERSION)
        self.assertTrue(organizations["organizations"])


if __name__ == "__main__":
    unittest.main()
