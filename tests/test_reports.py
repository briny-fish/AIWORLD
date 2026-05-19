import json
import tempfile
import unittest
from pathlib import Path

from virtual_society import Simulation
from virtual_society.experiment import run_experiment
from virtual_society.health import assess_metrics
from virtual_society.history import HistoryRecorder
from virtual_society.reports import (
    build_experiment_record,
    build_run_record,
    render_experiment_html,
    render_run_html,
    write_json,
)


class ReportTests(unittest.TestCase):
    def test_build_run_record_contains_metrics_agents_and_events(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(5)
        findings = assess_metrics(metrics)

        record = build_run_record(7, metrics, simulation.world, findings)

        self.assertEqual(record["seed"], 7)
        self.assertEqual(len(record["metrics"]), 5)
        self.assertEqual(len(record["agents"]), 6)
        self.assertEqual(len(record["organizations"]), 4)
        self.assertGreaterEqual(len(record["locations"]), 5)
        self.assertIn("reputation", record["agents"][0])
        self.assertIn("location_id", record["agents"][0])
        self.assertIn("social_findings", record)
        self.assertTrue(record["events"])

    def test_build_run_record_can_include_cognition_trace(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        trace = [
            {
                "day": 1,
                "agent_id": "a1",
                "agent_name": "Ari",
                "status": "primary",
                "baseline_plan": {"action": "farm", "reason": "food"},
                "proposed_plan": {"action": "repair", "reason": "storm"},
                "used_plan": {"action": "repair", "reason": "storm"},
                "diverged_from_baseline": True,
                "error": None,
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            cognition_trace=trace,
        )
        html = render_run_html(record)

        self.assertEqual(record["cognition_trace"], trace)
        self.assertIn("Cognition Trace", html)
        self.assertIn("divergence rate 100%", html)
        self.assertIn("storm", html)

    def test_run_html_renders_observer_sections(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(5)
        record = build_run_record(7, metrics, simulation.world, assess_metrics(metrics))

        html = render_run_html(record)

        self.assertIn("Virtual Society Run", html)
        self.assertIn("Metrics", html)
        self.assertIn("Organizations", html)
        self.assertIn("Locations", html)
        self.assertIn("Social Evaluation", html)
        self.assertIn("Recent Events", html)

    def test_run_html_renders_history_when_recorded(self) -> None:
        recorder = HistoryRecorder(seed=7, interval_days=3)
        simulation = Simulation(seed=7)
        metrics = simulation.run(6, after_step=recorder.capture)
        recorder.capture(simulation.world, metrics[-1], force=True)
        history = recorder.record(metrics)
        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            history=history,
        )

        html = render_run_html(record)

        self.assertIn("History", html)
        self.assertIn("Day 1", html)

    def test_experiment_html_renders_seed_comparison(self) -> None:
        reports = run_experiment(seeds=[1, 2], days=10)
        record = build_experiment_record(reports)

        html = render_experiment_html(record)

        self.assertIn("Virtual Society Experiment", html)
        self.assertIn("Seed Comparison", html)

    def test_write_json_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"

            write_json(path, {"ok": True})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})


if __name__ == "__main__":
    unittest.main()
