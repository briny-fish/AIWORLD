import unittest

from virtual_society import Simulation
from virtual_society.model import Event
from virtual_society.scar_diagnosis import assess_scar_bottlenecks


class ScarDiagnosisTests(unittest.TestCase):
    def test_relationship_crisis_without_contact_reports_missing_repair(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.20
        second.relationships[first.id] = 0.20
        simulation.world.day = 5
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 1

        items = assess_scar_bottlenecks(simulation.world)

        relationship = next(item for item in items if item.kind == "relationship_crisis")
        self.assertEqual(relationship.status, "no_direct_social_repair")
        self.assertEqual(relationship.metrics["direct_contacts"], 0)
        self.assertGreater(relationship.metrics["trust_gap"], 0)

    def test_relationship_contact_below_threshold_reports_remaining_gap(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.30
        second.relationships[first.id] = 0.30
        simulation.world.day = 5
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 1
        simulation.world.event_log.append(
            Event(
                day=3,
                kind="social",
                actor_id=first.id,
                description=f"{first.name} strengthened ties with {second.name}.",
            )
        )

        items = assess_scar_bottlenecks(simulation.world)

        relationship = next(item for item in items if item.kind == "relationship_crisis")
        self.assertEqual(relationship.status, "repair_below_threshold")
        self.assertEqual(relationship.metrics["direct_contacts"], 1)

    def test_blocked_route_reports_material_starvation(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        route_key = "commons|north_field"
        simulation.world.day = 12
        simulation.world.blocked_routes[route_key] = 0.75
        for location in simulation.world.locations:
            if location.id == "workshop":
                location.resources["materials"] = 0.0
        simulation.world.event_log.append(
            Event(
                day=8,
                kind="route_blocked",
                actor_id="society",
                description=f"Route {route_key} blocked after heavy strain.",
            )
        )

        items = assess_scar_bottlenecks(simulation.world)

        route = next(item for item in items if item.kind == "blocked_route")
        self.assertEqual(route.status, "material_starved")
        self.assertEqual(route.metrics["started_day"], 8)
        self.assertEqual(route.metrics["workshop_materials"], 0.0)

    def test_relationship_above_threshold_needs_final_social_contact(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.50
        second.relationships[first.id] = 0.50
        simulation.world.rules.relationship_repair_threshold = 0.42
        simulation.world.day = 5
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 1

        items = assess_scar_bottlenecks(simulation.world)

        relationship = next(item for item in items if item.kind == "relationship_crisis")
        self.assertEqual(relationship.status, "ready_but_unreconciled")
        self.assertEqual(relationship.severity, "info")
        self.assertEqual(relationship.metrics["trust_gap"], 0.0)


if __name__ == "__main__":
    unittest.main()
