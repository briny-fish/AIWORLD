import json
import unittest

from virtual_society import Simulation, build_luanti_scene, build_social_feed, build_world_client_frame


class LuantiExportTests(unittest.TestCase):
    def test_luanti_scene_exports_static_voxel_mapping(self) -> None:
        simulation = Simulation(seed=7, world_preset="generative_alpha")
        simulation.run(3)
        simulation.world.blocked_routes["commons|north_field"] = 0.75
        frame = build_world_client_frame(
            simulation.world,
            seed=7,
            world_preset="generative_alpha",
            social_feed=build_social_feed(simulation.world, limit=10),
        )

        scene = build_luanti_scene(frame)

        self.assertEqual(scene["kind"], "luanti_scene")
        self.assertEqual(scene["version"], "luanti-scene-v1")
        self.assertEqual(scene["source"]["version"], "world-client-v1")
        self.assertTrue(scene["nodes"])
        self.assertTrue(scene["entities"])
        self.assertTrue(scene["social_log"])
        self.assertTrue(
            any(item["node"] == "aiworld_bridge:route_blocked" for item in scene["nodes"])
        )
        registered_nodes = set(scene["materials"])
        self.assertTrue(
            all(item["node"] in registered_nodes for item in scene["nodes"]),
            {item["node"] for item in scene["nodes"]} - registered_nodes,
        )
        self.assertEqual(len(scene["entities"]), len(frame["agents"]))
        json.dumps(scene, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
