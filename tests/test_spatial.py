import unittest

from virtual_society import Simulation
from virtual_society.interventions import Intervention
from virtual_society.model import Action, Plan


class SpatialTests(unittest.TestCase):
    def test_initial_world_has_locations_and_agent_positions(self) -> None:
        simulation = Simulation(seed=7)

        location_ids = {location.id for location in simulation.world.locations}
        agent_locations = {agent.location_id for agent in simulation.world.agents}

        self.assertIn("commons", location_ids)
        self.assertIn("north_field", location_ids)
        self.assertTrue(agent_locations.issubset(location_ids))

    def test_actions_move_agents_to_expected_locations(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        agent.needs.energy = 1.0
        agent.needs.food = 1.0

        simulation._apply_action(agent, Plan(Action.GATHER, 1.0, "test"))

        self.assertEqual(agent.location_id, "woodlot")

    def test_location_condition_changes_with_work_and_repair(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        workshop = next(location for location in simulation.world.locations if location.id == "workshop")
        field_before = field.condition
        workshop_before = workshop.condition

        simulation._apply_action(agent, Plan(Action.FARM, 1.0, "test"))
        simulation._apply_action(agent, Plan(Action.REPAIR, 1.0, "test"))

        self.assertLess(field.condition, field_before)
        self.assertGreater(workshop.condition, workshop_before)

    def test_location_resources_stay_in_sync_with_global_totals(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        before_field_food = field.resources["food"]

        simulation._apply_action(agent, Plan(Action.FARM, 1.0, "test"))

        location_food = sum(location.resources["food"] for location in simulation.world.locations)
        self.assertGreater(field.resources["food"], before_field_food)
        self.assertAlmostEqual(simulation.world.resources["food"], location_food)

    def test_location_specialization_changes_production(self) -> None:
        high_output = Simulation(seed=7)
        low_output = Simulation(seed=7)
        high_agent = high_output.world.agents[0]
        low_agent = low_output.world.agents[0]
        high_field = next(location for location in high_output.world.locations if location.id == "north_field")
        low_field = next(location for location in low_output.world.locations if location.id == "north_field")
        high_field.resources["food"] = 0.0
        low_field.resources["food"] = 0.0
        high_field.production["food"] = 2.0
        low_field.production["food"] = 0.5

        high_output._apply_action(high_agent, Plan(Action.FARM, 1.0, "test"))
        low_output._apply_action(low_agent, Plan(Action.FARM, 1.0, "test"))

        self.assertGreater(high_field.resources["food"], low_field.resources["food"])

    def test_haul_moves_food_to_depot_without_creating_resources(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        for location in simulation.world.locations:
            location.resources["food"] = 0.0
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        commons = next(location for location in simulation.world.locations if location.id == "commons")
        field.resources["food"] = 5.0
        simulation._sync_world_resources()
        before_total = simulation.world.resources["food"]

        simulation._apply_action(agent, Plan(Action.HAUL, 1.0, "test"))

        self.assertGreater(commons.resources["food"], 0.0)
        self.assertLess(field.resources["food"], 5.0)
        self.assertAlmostEqual(simulation.world.resources["food"], before_total)
        self.assertTrue(any(load > 0.0 for load in simulation.world.route_loads.values()))

    def test_supply_routes_move_food_to_depot_before_meals(self) -> None:
        simulation = Simulation(seed=7)
        for location in simulation.world.locations:
            location.resources["food"] = 0.0
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        commons = next(location for location in simulation.world.locations if location.id == "commons")
        field.resources["food"] = 4.0
        simulation._sync_world_resources()
        before_total = simulation.world.resources["food"]

        simulation._apply_supply_routes()

        self.assertGreater(commons.resources["food"], 0.0)
        self.assertLess(field.resources["food"], 4.0)
        self.assertAlmostEqual(simulation.world.resources["food"], before_total)

    def test_routes_have_network_distance(self) -> None:
        simulation = Simulation(seed=7)

        self.assertEqual(simulation._route_distance("north_field", "commons"), 1)
        self.assertEqual(simulation._route_distance("north_field", "shelter_house"), 2)

    def test_disconnected_routes_block_hauling(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        for location in simulation.world.locations:
            location.connected_location_ids = []
            location.resources["food"] = 0.0
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        commons = next(location for location in simulation.world.locations if location.id == "commons")
        field.resources["food"] = 5.0
        simulation._sync_world_resources()

        simulation._apply_action(agent, Plan(Action.HAUL, 1.0, "test"))

        self.assertEqual(commons.resources["food"], 0.0)
        self.assertEqual(field.resources["food"], 5.0)
        self.assertEqual(simulation.world.event_log[-1].kind, "rest")

    def test_common_maintenance_consumes_materials_and_repairs_location(self) -> None:
        simulation = Simulation(seed=7)
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        workshop = next(location for location in simulation.world.locations if location.id == "workshop")
        field.condition = 0.30
        workshop.resources["materials"] = 1.0
        simulation._sync_world_resources()

        simulation._apply_common_maintenance()

        self.assertGreater(field.condition, 0.30)
        self.assertLess(workshop.resources["materials"], 1.0)
        self.assertEqual(simulation.world.event_log[-1].kind, "maintenance")

    def test_route_strain_wears_connected_locations(self) -> None:
        simulation = Simulation(seed=7)
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        commons = next(location for location in simulation.world.locations if location.id == "commons")
        field.condition = 1.0
        commons.condition = 1.0
        simulation.world.route_loads["commons|north_field"] = 20.0

        simulation._apply_route_wear()

        self.assertLess(field.condition, 1.0)
        self.assertLess(commons.condition, 1.0)
        self.assertEqual(simulation.world.event_log[-1].kind, "route_strain")

    def test_shelter_upkeep_depreciates_shelter_stock(self) -> None:
        simulation = Simulation(seed=7)
        before = simulation.world.resources["shelter"]

        simulation._apply_shelter_upkeep()

        self.assertLess(simulation.world.resources["shelter"], before)

    def test_meals_consume_only_shared_depot_food(self) -> None:
        simulation = Simulation(seed=7)
        for location in simulation.world.locations:
            location.resources["food"] = 0.0
        field = next(location for location in simulation.world.locations if location.id == "north_field")
        field.resources["food"] = 100.0
        simulation._sync_world_resources()

        simulation._consume_food()

        self.assertEqual(field.resources["food"], 100.0)

    def test_new_agent_can_join_known_location(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.day = 1

        simulation.apply_intervention(
            Intervention(
                day=1,
                kind="new_agent",
                params={"name": "Gale", "role": "scout", "location_id": "woodlot"},
            )
        )

        self.assertEqual(simulation.world.agents[-1].location_id, "woodlot")


if __name__ == "__main__":
    unittest.main()
