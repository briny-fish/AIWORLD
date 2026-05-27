import json
import threading
import unittest
from dataclasses import asdict
from urllib.request import Request, urlopen

from virtual_society import Simulation, SimulationService
from virtual_society.api import make_server


class ApiTests(unittest.TestCase):
    def test_service_step_matches_direct_simulation(self) -> None:
        direct_metrics = Simulation(seed=7).run(8)
        service = SimulationService(seed=7, snapshot_interval_days=4)

        result = service.step(days=8)

        self.assertEqual(result["final_metrics"], asdict(direct_metrics[-1]))
        self.assertEqual(service.state()["world"]["day"], 8)
        self.assertEqual(service.history()["snapshot_count"], 3)

    def test_service_schedules_intervention_for_next_day(self) -> None:
        service = SimulationService(seed=7)

        service.schedule_intervention(
            {
                "kind": "resource",
                "reason": "api test",
                "params": {"resource": "food", "amount": 3},
            }
        )
        result = service.step(days=1)
        events = service.events(limit=100)["events"]

        self.assertEqual(result["applied_interventions"][0]["day"], 1)
        self.assertTrue(any(event["kind"] == "intervention" for event in events))

    def test_service_returns_agent_dossier(self) -> None:
        service = SimulationService(seed=7, world_preset="generative_alpha")
        service.step(days=3)

        dossier = service.agent_dossier("a1")

        self.assertEqual(dossier["agent"]["id"], "a1")
        self.assertTrue(dossier["agent"]["recent_life_journal"])
        self.assertTrue(dossier["relationship_links"])
        self.assertEqual(dossier["day"], 3)

    def test_http_state_step_and_report_endpoints(self) -> None:
        service = SimulationService(seed=7, snapshot_interval_days=2)
        server = make_server(service, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            health = _get_json(f"{base_url}/health")
            step = _post_json(f"{base_url}/step", {"days": 3})
            state = _get_json(f"{base_url}/state")
            agent = _get_json(f"{base_url}/agents/a1")
            report_html = _get_text(f"{base_url}/report/run.html")
            observer_html = _get_text(f"{base_url}/observer")
            observer3d_html = _get_text(f"{base_url}/observer3d")

            self.assertEqual(health["status"], "ok")
            self.assertEqual(step["current_day"], 3)
            self.assertEqual(state["world"]["day"], 3)
            self.assertEqual(agent["agent"]["id"], "a1")
            self.assertTrue(agent["agent"]["recent_life_journal"])
            self.assertIn("Virtual Society Run", report_html)
            self.assertIn("History", report_html)
            self.assertIn("Virtual Society Observer", observer_html)
            self.assertIn("Step 1 Day", observer_html)
            self.assertIn("Step 30 Days", observer_html)
            self.assertIn("World Pulse", observer_html)
            self.assertIn("Selected Agent", observer_html)
            self.assertIn("/agents/", observer_html)
            self.assertIn("Virtual Society 3D Observer", observer3d_html)
            self.assertIn("three", observer3d_html)
            self.assertIn("WebGLRenderer", observer3d_html)
            self.assertIn("/agents/", observer3d_html)
            self.assertIn("Life Timeline", observer3d_html)
            self.assertIn("Food at Location", observer3d_html)
            self.assertIn("30 Days", observer3d_html)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_http_intervention_endpoint_schedules_and_applies(self) -> None:
        service = SimulationService(seed=7)
        server = make_server(service, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            scheduled = _post_json(
                f"{base_url}/interventions",
                {
                    "kind": "broadcast",
                    "reason": "api test",
                    "params": {"tone": "hope", "strength": 0.05},
                },
            )
            _post_json(f"{base_url}/step", {"days": 1})
            events = _get_json(f"{base_url}/events?limit=100")

            self.assertEqual(scheduled["scheduled"]["day"], 1)
            self.assertTrue(any(event["kind"] == "broadcast" for event in events["events"]))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_text(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
