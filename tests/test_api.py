import json
import threading
import unittest
from dataclasses import asdict
from urllib.request import Request, urlopen

from virtual_society import HybridCognition, HybridCognitionConfig, Simulation, SimulationService
from virtual_society.api import make_server
from virtual_society.model import Action, Plan


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
        index = service.agent_dossiers()
        location = service.location_dossier("commons")
        locations = service.location_dossiers()
        organization = service.organization_dossier("common_council")
        organizations = service.organization_dossiers()

        self.assertEqual(dossier["kind"], "agent_dossier")
        self.assertIn("continuity", dossier)
        self.assertEqual(dossier["agent"]["id"], "a1")
        self.assertTrue(dossier["agent"]["recent_life_journal"])
        self.assertTrue(dossier["relationship_links"])
        self.assertTrue(dossier["observer_affordances"])
        self.assertEqual(dossier["day"], 3)
        self.assertEqual(index["kind"], "agent_dossier_index")
        self.assertEqual(len(index["agents"]), 12)
        self.assertEqual(location["kind"], "location_dossier")
        self.assertEqual(locations["kind"], "location_dossier_index")
        self.assertEqual(organization["kind"], "organization_dossier")
        self.assertEqual(organizations["kind"], "organization_dossier_index")

    def test_service_exposes_live_provider_status_and_trace(self) -> None:
        cognition = HybridCognition(
            primary=_FixedProvider(),
            config=HybridCognitionConfig(
                agent_ids={"a1"},
                every_days=1,
                max_calls=1,
                counterfactual_horizon_days=0,
            ),
        )
        service = SimulationService(
            seed=7,
            world_preset="generative_alpha",
            cognition=cognition,
        )

        before = service.provider_status()
        service.step(days=1)
        after = service.provider_status()
        record = service.run_record()

        self.assertTrue(before["live_llm_enabled"])
        self.assertEqual(before["surfaces"]["cognition"]["model"], "test-model")
        self.assertEqual(after["surfaces"]["cognition"]["stats"]["llm_attempts"], 1)
        self.assertEqual(after["surfaces"]["cognition"]["trace_length"], 1)
        self.assertEqual(len(record["cognition_trace"]), 1)

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
            provider_status = _get_json(f"{base_url}/provider-status")
            social_feed = _get_json(f"{base_url}/social-feed?limit=20")
            world_frame = _get_json(f"{base_url}/client/world-frame")
            agent = _get_json(f"{base_url}/agents/a1")
            social_history = _get_json(f"{base_url}/agents/a1/social-history?limit=10")
            agents = _get_json(f"{base_url}/agents")
            location = _get_json(f"{base_url}/locations/commons")
            locations = _get_json(f"{base_url}/locations")
            organization = _get_json(f"{base_url}/organizations/common_council")
            organizations = _get_json(f"{base_url}/organizations")
            report_html = _get_text(f"{base_url}/report/run.html")
            observer_html = _get_text(f"{base_url}/observer")
            observer3d_html = _get_text(f"{base_url}/observer3d")

            self.assertEqual(health["status"], "ok")
            self.assertEqual(step["current_day"], 3)
            self.assertEqual(state["world"]["day"], 3)
            self.assertEqual(provider_status["kind"], "provider_status")
            self.assertFalse(provider_status["live_llm_enabled"])
            self.assertEqual(social_feed["kind"], "social_feed")
            self.assertEqual(world_frame["kind"], "world_client_frame")
            self.assertEqual(world_frame["version"], "world-client-v1")
            self.assertTrue(world_frame["agents"])
            self.assertTrue(world_frame["locations"])
            self.assertTrue(world_frame["routes"])
            self.assertIn("command_endpoints", world_frame)
            self.assertEqual(social_history["kind"], "agent_social_history")
            self.assertEqual(agent["agent"]["id"], "a1")
            self.assertEqual(agent["version"], "agent-dossier-v1")
            self.assertIn("continuity", agent)
            self.assertIn("social_history", agent)
            self.assertIn("influence_chains", agent)
            self.assertTrue(agent["agent"]["recent_life_journal"])
            self.assertEqual(agents["kind"], "agent_dossier_index")
            self.assertTrue(agents["agents"])
            self.assertEqual(location["version"], "world-object-dossier-v1")
            self.assertEqual(locations["kind"], "location_dossier_index")
            self.assertEqual(organization["kind"], "organization_dossier")
            self.assertEqual(organizations["kind"], "organization_dossier_index")
            self.assertIn("Virtual Society Run", report_html)
            self.assertIn("History", report_html)
            self.assertIn("Virtual Society Observer", observer_html)
            self.assertIn("Step 1 Day", observer_html)
            self.assertIn("Step 30 Days", observer_html)
            self.assertIn("World Pulse", observer_html)
            self.assertIn("Selected Agent", observer_html)
            self.assertIn("Social Feed", observer_html)
            self.assertIn("Conversation History", observer_html)
            self.assertIn("Influence Chain", observer_html)
            self.assertIn("/provider-status", observer_html)
            self.assertIn("/social-feed", observer_html)
            self.assertIn("/social-history", observer_html)
            self.assertIn("Provider", observer_html)
            self.assertIn("/agents/", observer_html)
            self.assertIn("observer_affordances", observer_html)
            self.assertIn("Virtual Society 3D Observer", observer3d_html)
            self.assertIn("three", observer3d_html)
            self.assertIn("WebGLRenderer", observer3d_html)
            self.assertIn("/client/world-frame", observer3d_html)
            self.assertIn("/agents/", observer3d_html)
            self.assertIn("observer_affordances", observer3d_html)
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


class _FixedProvider:
    model = "test-model"
    reasoning_effort = "test"

    def propose_plan_with_baseline(self, agent, world, baseline_plan):
        return Plan(
            action=Action.REST,
            priority=0.7,
            reason="test provider selected rest",
            target_id=None,
            horizon_days=1,
        )


if __name__ == "__main__":
    unittest.main()
