import unittest

from virtual_society import Simulation
from virtual_society.interventions import Intervention
from virtual_society.observer_recommendations import (
    build_observer_recommendations,
    intervention_payloads,
)
from virtual_society.scar_diagnosis import assess_scar_bottlenecks


class ObserverRecommendationTests(unittest.TestCase):
    def test_material_starved_route_recommends_workshop_resource(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.world.day = 30
        simulation.world.blocked_routes["commons|north_field"] = 0.75
        for location in simulation.world.locations:
            if location.id == "workshop":
                location.resources["materials"] = 0.0

        scars = [item.as_dict() for item in assess_scar_bottlenecks(simulation.world)]
        recommendations = build_observer_recommendations(simulation.world, scars)

        first = recommendations[0].as_dict()
        self.assertEqual(first["intervention"]["kind"], "resource")
        self.assertEqual(first["intervention"]["day"], 31)
        self.assertEqual(first["intervention"]["params"]["resource"], "materials")
        self.assertEqual(first["intervention"]["params"]["location_id"], "workshop")
        self.assertIn("blocked routes", first["title"])

    def test_relationship_crisis_recommends_targeted_broadcast(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.20
        second.relationships[first.id] = 0.20
        simulation.world.day = 8
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 2

        scars = [item.as_dict() for item in assess_scar_bottlenecks(simulation.world)]
        recommendations = build_observer_recommendations(simulation.world, scars)

        intervention = recommendations[0].as_dict()["intervention"]
        self.assertEqual(intervention["kind"], "broadcast")
        self.assertEqual(intervention["params"]["intent"], "reconcile_relationships")
        self.assertEqual(intervention["params"]["target_agent_ids"], [first.id, second.id])

    def test_ready_relationship_crisis_recommends_mediation(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.44
        second.relationships[first.id] = 0.44
        simulation.world.day = 8
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 2

        scars = [item.as_dict() for item in assess_scar_bottlenecks(simulation.world)]
        recommendations = build_observer_recommendations(simulation.world, scars)

        intervention = recommendations[0].as_dict()["intervention"]
        self.assertEqual(intervention["kind"], "mediation")
        self.assertEqual(intervention["params"]["target_agent_ids"], [first.id, second.id])

    def test_near_threshold_relationship_crisis_recommends_mediation(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        first.relationships[second.id] = 0.37
        second.relationships[first.id] = 0.37
        simulation.world.day = 8
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 2

        scars = [item.as_dict() for item in assess_scar_bottlenecks(simulation.world)]
        recommendations = build_observer_recommendations(simulation.world, scars)

        intervention = recommendations[0].as_dict()["intervention"]
        self.assertEqual(intervention["kind"], "mediation")
        self.assertEqual(intervention["params"]["target_agent_ids"], [first.id, second.id])

    def test_recommendations_export_valid_intervention_payloads(self) -> None:
        simulation = Simulation(seed=7)
        first = simulation.world.agents[0]
        second = simulation.world.agents[1]
        simulation.world.day = 8
        simulation.world.relationship_crises[f"{first.id}|{second.id}"] = 2

        scars = [item.as_dict() for item in assess_scar_bottlenecks(simulation.world)]
        recommendations = [
            item.as_dict()
            for item in build_observer_recommendations(simulation.world, scars)
        ]
        payloads = intervention_payloads(recommendations)

        parsed = [Intervention.from_dict(item) for item in payloads]
        self.assertTrue(parsed)
        self.assertEqual(parsed[0].actor_id, "The_Envoy")


if __name__ == "__main__":
    unittest.main()
