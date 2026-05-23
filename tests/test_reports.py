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
    build_rule_baseline_comparison,
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

    def test_build_run_record_can_include_reflection_trace(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        trace = [
            {
                "day": 7,
                "agent_id": "a1",
                "agent_name": "Ari",
                "status": "primary",
                "baseline_reflection": "Ari saw a routine week.",
                "proposed_reflection": "Ari treated the storm as a duty.",
                "used_reflection": "Ari treated the storm as a duty.",
                "focus": "shock",
                "memory_refs": [0, 2],
                "error": None,
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            reflection_trace=trace,
        )
        html = render_run_html(record)

        self.assertEqual(record["reflection_trace"], trace)
        self.assertIn("Reflection Trace", html)
        self.assertIn("memory grounded 1", html)
        self.assertIn("storm as a duty", html)

    def test_build_run_record_can_include_reflection_follow_through(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        follow_through = [
            {
                "day": 21,
                "agent_id": "a1",
                "agent_name": "Ari",
                "status": "primary",
                "focus": "scarcity",
                "signal": "baseline_action_diverged",
                "window_start": 22,
                "window_end": 28,
                "reflection_summary": "Ari kept food security salient.",
                "plan_evidence": [{"day": 22, "kind": "plan", "text": "farm", "overlap_terms": ["food"]}],
                "dialogue_evidence": [],
                "baseline_plan_deltas": [
                    {
                        "day": 22,
                        "run_plan": "day 22: farm | food pressure",
                        "baseline_plan": "day 22: gather | routine",
                        "run_action": "farm",
                        "baseline_action": "gather",
                        "change_kind": "action",
                    }
                ],
                "summary": "Ari changed plan history after the reflection.",
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            reflection_follow_through=follow_through,
        )
        html = render_run_html(record)

        self.assertEqual(record["reflection_follow_through"], follow_through)
        self.assertIn("Reflection Follow-through", html)
        self.assertIn("baseline_action_diverged", html)
        self.assertIn("Ari changed plan history", html)
        self.assertIn("day 22: farm", html)

    def test_build_run_record_can_include_dialogue_trace(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        trace = [
            {
                "day": 21,
                "speaker_id": "a1",
                "speaker_name": "Ari",
                "partner_id": "a2",
                "partner_name": "Bo",
                "status": "primary",
                "baseline_dialogue": "Ari and Bo discussed routine work.",
                "proposed_dialogue": "Ari asked Bo to keep food distribution visible.",
                "used_dialogue": "Ari asked Bo to keep food distribution visible.",
                "focus": "coordination",
                "memory_refs": [0],
                "error": None,
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            dialogue_trace=trace,
        )
        html = render_run_html(record)

        self.assertEqual(record["dialogue_trace"], trace)
        self.assertIn("Dialogue Trace", html)
        self.assertIn("memory grounded 1", html)
        self.assertIn("food distribution visible", html)

    def test_build_run_record_can_include_dialogue_follow_through(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        follow_through = [
            {
                "day": 21,
                "speaker_id": "a1",
                "speaker_name": "Ari",
                "partner_id": "a2",
                "partner_name": "Bo",
                "status": "primary",
                "focus": "coordination",
                "signal": "baseline_reflection_context_diverged",
                "window_start": 22,
                "window_end": 35,
                "generated_dialogue": "Ari asked Bo to keep food distribution visible.",
                "baseline_dialogue": "Ari and Bo discussed routine work.",
                "memory_evidence": [
                    {
                        "day": 21,
                        "agent_id": "a1",
                        "agent_name": "Ari",
                        "kind": "dialogue",
                        "text": "Ari asked Bo to keep food distribution visible.",
                        "overlap_terms": ["food"],
                    }
                ],
                "reflection_evidence": [],
                "plan_evidence": [],
                "baseline_reflection_deltas": [
                    {
                        "day": 28,
                        "agent_id": "a1",
                        "agent_name": "Ari",
                        "run_text": "day 28: Ari kept food distribution salient.",
                        "baseline_text": "day 28: Ari reflected on routine labor.",
                        "change_kind": "context",
                    }
                ],
                "baseline_plan_deltas": [],
                "summary": "Ari and Bo carried generated dialogue into later reflection.",
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            dialogue_follow_through=follow_through,
        )
        html = render_run_html(record)

        self.assertEqual(record["dialogue_follow_through"], follow_through)
        self.assertIn("Dialogue Follow-through", html)
        self.assertIn("baseline_reflection_context_diverged", html)
        self.assertIn("food distribution salient", html)

    def test_build_rule_baseline_comparison_records_final_deltas(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(5)
        baseline = Simulation(seed=7)
        baseline_metrics = baseline.run(5)
        comparison = build_rule_baseline_comparison(
            metrics,
            baseline_metrics,
            assess_metrics(baseline_metrics),
            [],
        )

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            baseline_comparison=comparison,
        )
        html = render_run_html(record)

        self.assertEqual(comparison["deltas"]["average_need"], 0.0)
        self.assertIn("Rule Baseline Comparison", html)
        self.assertIn("average need 0", html)

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
