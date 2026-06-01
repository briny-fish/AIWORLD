import json
import unittest

from virtual_society import (
    WORLD_CLIENT_PROTOCOL_VERSION,
    Simulation,
    build_social_feed,
    build_world_client_frame,
)


class WorldClientProtocolTests(unittest.TestCase):
    def test_world_client_frame_exposes_renderable_world_contract(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(3)
        simulation.world.blocked_routes["commons|north_field"] = 0.75

        frame = build_world_client_frame(
            simulation.world,
            seed=7,
            world_preset="generative_alpha",
            provider_status={
                "live_llm_enabled": True,
                "models": ["gpt-5.5"],
                "surfaces": {
                    "cognition": {
                        "mode": "hybrid",
                        "provider": "HybridCognition",
                        "primary_provider": "OpenAICognition",
                        "model": "gpt-5.5",
                        "trace_length": 1,
                        "stats": {"llm_attempts": 1},
                    }
                },
            },
            social_feed=build_social_feed(simulation.world, limit=10),
        )

        self.assertEqual(frame["kind"], "world_client_frame")
        self.assertEqual(frame["version"], WORLD_CLIENT_PROTOCOL_VERSION)
        self.assertEqual(frame["seed"], 7)
        self.assertEqual(frame["world_preset"], "generative_alpha")
        self.assertEqual(frame["provider"]["models"], ["gpt-5.5"])
        self.assertEqual(frame["coordinate_system"]["up_axis"], "y")
        self.assertEqual(len(frame["agents"]), len(simulation.world.agents))
        self.assertEqual(len(frame["locations"]), len(simulation.world.locations))
        self.assertTrue(frame["routes"])
        self.assertTrue(frame["organizations"])
        self.assertTrue(frame["social_feed"])
        self.assertTrue(frame["affordances"])
        self.assertTrue(
            any(route["blocked"] for route in frame["routes"]),
            frame["routes"],
        )
        self.assertTrue(
            any(affordance["endpoint"] == "/step" for affordance in frame["affordances"])
        )
        json.dumps(frame, ensure_ascii=False)

    def test_world_client_frame_does_not_leak_mutable_world_objects(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(1)

        first = build_world_client_frame(simulation.world, seed=7)
        second = build_world_client_frame(simulation.world, seed=7)
        self.assertEqual(first, second)

        location_id = first["locations"][0]["id"]
        before = next(
            location.resources.get("food", 0.0)
            for location in simulation.world.locations
            if location.id == location_id
        )
        first["locations"][0]["resources"]["food"] = 999.0
        after = next(
            location.resources.get("food", 0.0)
            for location in simulation.world.locations
            if location.id == location_id
        )

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
