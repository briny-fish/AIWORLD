import unittest

from virtual_society import Simulation
from virtual_society.interventions import Intervention


class InstitutionTests(unittest.TestCase):
    def test_initial_world_has_households_and_council(self) -> None:
        simulation = Simulation(seed=7)

        self.assertEqual(
            [organization.id for organization in simulation.world.organizations],
            ["household_north", "household_south", "common_council", "maker_guild"],
        )
        self.assertTrue(all(agent.organization_ids for agent in simulation.world.agents))

        metrics = simulation.metrics()
        self.assertGreater(metrics.average_reputation, 0.0)
        self.assertGreater(metrics.institutional_cohesion, 0.0)

    def test_actions_change_reputation_and_cohesion(self) -> None:
        simulation = Simulation(seed=7)
        starting_reputation = [agent.reputation for agent in simulation.world.agents]
        starting_cohesion = [organization.cohesion for organization in simulation.world.organizations]

        simulation.run(10)

        self.assertNotEqual(
            [agent.reputation for agent in simulation.world.agents],
            starting_reputation,
        )
        self.assertNotEqual(
            [organization.cohesion for organization in simulation.world.organizations],
            starting_cohesion,
        )

    def test_organization_intervention_creates_membership(self) -> None:
        simulation = Simulation(seed=7)

        simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="organization",
                    params={
                        "id": "water_circle",
                        "name": "Water Circle",
                        "kind": "guild",
                        "home_location_id": "woodlot",
                        "members": ["a1", "a4"],
                        "norms": ["maintain_wells"],
                        "inventory_targets": {"materials": 1.5},
                        "exchange_preferences": {"materials": 1.0},
                        "cohesion": 0.62,
                    },
                )
            ],
        )

        organization = next(
            item for item in simulation.world.organizations if item.id == "water_circle"
        )
        self.assertEqual(organization.members, ["a1", "a4"])
        self.assertEqual(organization.home_location_id, "woodlot")
        self.assertEqual(organization.inventory_targets["materials"], 1.5)
        self.assertIn("water_circle", simulation.world.agents[0].organization_ids)
        self.assertTrue(any(event.kind == "organization" for event in simulation.world.event_log))

    def test_organization_exchange_moves_surplus_to_deficit(self) -> None:
        simulation = Simulation(seed=7)
        north_field = next(location for location in simulation.world.locations if location.id == "north_field")
        shelter = next(location for location in simulation.world.locations if location.id == "shelter_house")
        north_field.resources["food"] = 6.0
        shelter.resources["food"] = 0.0
        simulation._sync_world_resources()

        simulation._apply_organization_exchange()

        self.assertGreater(shelter.resources["food"], 0.0)
        self.assertLess(north_field.resources["food"], 6.0)
        self.assertTrue(any(event.kind == "exchange" for event in simulation.world.event_log))
        self.assertTrue(any(load > 0.0 for load in simulation.world.route_loads.values()))

    def test_low_institutional_cohesion_triggers_crisis_pressure(self) -> None:
        simulation = Simulation(seed=7)
        for organization in simulation.world.organizations:
            organization.cohesion = 0.10
        before_belonging = [
            agent.needs.belonging for agent in simulation.world.agents
        ]

        simulation.run(1)

        self.assertTrue(
            any(event.kind == "institutional_crisis" for event in simulation.world.event_log)
        )
        self.assertTrue(
            any(
                agent.needs.belonging < before
                for agent, before in zip(simulation.world.agents, before_belonging)
            )
        )


if __name__ == "__main__":
    unittest.main()
