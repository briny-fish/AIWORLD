import json
import tempfile
import unittest
from pathlib import Path

from virtual_society import Simulation
from virtual_society.experiment import run_experiment
from virtual_society.health import assess_metrics
from virtual_society.history import HistoryRecorder
from virtual_society.interventions import Intervention
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
                "counterfactual": {
                    "horizon_days": 3,
                    "score_delta": 0.04,
                    "recommendation": "proposed",
                    "baseline": {"score": 5.1},
                    "proposed": {"score": 5.14},
                },
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
        self.assertIn("delta +0.04", html)

    def test_build_run_record_can_include_counterfactual_evaluation(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        counterfactual_evaluation = {
            "total": 1,
            "accepted": 1,
            "rejected": 0,
            "acceptance_rate": 1.0,
            "average_score_delta": 0.0174,
            "worst_score_delta": 0.0174,
            "best_score_delta": 0.0174,
            "summary": "Counterfactual probes accepted 1/1 proposals and rejected 0.",
            "by_agent": [
                {
                    "key": "a1",
                    "label": "Ari",
                    "total": 1,
                    "accepted": 1,
                    "rejected": 0,
                    "average_score_delta": 0.0174,
                    "worst_score_delta": 0.0174,
                    "best_score_delta": 0.0174,
                }
            ],
            "by_action_pair": [
                {
                    "key": "farm->rest",
                    "label": "farm -> rest",
                    "total": 1,
                    "accepted": 1,
                    "rejected": 0,
                    "average_score_delta": 0.0174,
                    "worst_score_delta": 0.0174,
                    "best_score_delta": 0.0174,
                }
            ],
        }

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            counterfactual_evaluation=counterfactual_evaluation,
        )
        html = render_run_html(record)

        self.assertEqual(record["counterfactual_evaluation"], counterfactual_evaluation)
        self.assertIn("Counterfactual Evaluation", html)
        self.assertIn("Acceptance Rate", html)
        self.assertIn("farm -&gt; rest", html)
        self.assertIn("+0.0174", html)

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

    def test_build_run_record_can_include_generated_chains(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        chains = [
            {
                "dialogue_day": 21,
                "reflection_day": 28,
                "speaker_id": "a1",
                "speaker_name": "Ari",
                "partner_id": "a2",
                "partner_name": "Bo",
                "reflection_agent_id": "a1",
                "reflection_agent_name": "Ari",
                "dialogue_focus": "coordination",
                "reflection_focus": "scarcity",
                "signal": "generated_chain_action_diverged",
                "shared_terms": ["food", "trust"],
                "generated_dialogue": "Ari asked Bo to keep food visible.",
                "generated_reflection": "Ari made food trust the priority.",
                "memory_evidence": [
                    {
                        "day": 21,
                        "agent_id": "a1",
                        "agent_name": "Ari",
                        "kind": "dialogue",
                        "text": "Ari asked Bo to keep food visible.",
                        "overlap_terms": ["food"],
                    }
                ],
                "plan_evidence": [],
                "baseline_plan_deltas": [
                    {
                        "day": 29,
                        "run_plan": "day 29: farm | food pressure",
                        "baseline_plan": "day 29: gather | routine",
                        "run_action": "farm",
                        "baseline_action": "gather",
                        "change_kind": "action",
                    }
                ],
                "summary": "Ari carried generated dialogue into generated reflection.",
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            generated_chains=chains,
        )
        html = render_run_html(record)

        self.assertEqual(record["generated_chains"], chains)
        self.assertIn("Generated Chain Evaluation", html)
        self.assertIn("generated_chain_action_diverged", html)
        self.assertIn("Ari carried generated dialogue", html)

    def test_build_run_record_can_include_cognition_impacts(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        impacts = [
            {
                "day": 21,
                "agent_id": "a1",
                "agent_name": "Ari",
                "status": "primary",
                "signal": "cognition_action_diverged",
                "baseline_action": "farm",
                "proposed_action": "rest",
                "used_action": "rest",
                "proposed_diverged_from_baseline": True,
                "used_diverged_from_baseline": True,
                "execution_evidence": [
                    {
                        "day": 21,
                        "agent_id": "a1",
                        "agent_name": "Ari",
                        "kind": "rest",
                        "text": "Ari rested.",
                        "effects": {"energy": 0.32},
                    }
                ],
                "baseline_plan_deltas": [
                    {
                        "day": 21,
                        "run_plan": "day 21: rest | generated recovery",
                        "baseline_plan": "day 21: farm | shared food stores are low",
                        "run_action": "rest",
                        "baseline_action": "farm",
                        "change_kind": "action",
                    }
                ],
                "summary": "Ari accepted generated rest over the rule baseline.",
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            cognition_impacts=impacts,
        )
        html = render_run_html(record)

        self.assertEqual(record["cognition_impacts"], impacts)
        self.assertIn("Cognition Impact Evaluation", html)
        self.assertIn("cognition_action_diverged", html)
        self.assertIn("Ari accepted generated rest", html)

    def test_build_run_record_can_include_cognition_outcomes(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        outcomes = [
            {
                "day": 21,
                "agent_id": "a1",
                "agent_name": "Ari",
                "cognition_signal": "cognition_action_diverged",
                "outcome_signal": "mixed_resource_gain_social_cost",
                "windows": [
                    {
                        "label": "final",
                        "day": 30,
                        "deltas": {
                            "average_need": -0.004,
                            "average_trust": -0.002,
                            "institutional_cohesion": 0.0,
                            "food": 0.91,
                            "materials": 0.11,
                            "shelter": -0.58,
                        },
                        "signal": "mixed_resource_gain_social_cost",
                    }
                ],
                "summary": "Ari's generated rest traded social cost for food.",
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            cognition_outcomes=outcomes,
        )
        html = render_run_html(record)

        self.assertEqual(record["cognition_outcomes"], outcomes)
        self.assertIn("Cognition Outcome Evaluation", html)
        self.assertIn("mixed_resource_gain_social_cost", html)
        self.assertIn("Ari&#x27;s generated rest", html)

    def test_build_run_record_can_include_llm_cache_summary(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(1)
        llm_cache = [
            {
                "surface": "cognition",
                "provider": "codex-cli",
                "mode": "read-only",
                "root_dir": "artifacts/llm-cache",
                "model": "gpt-5.4-mini",
                "reasoning_effort": "low",
                "reads": 1,
                "hits": 1,
                "misses": 0,
                "writes": 0,
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            llm_cache=llm_cache,
        )
        html = render_run_html(record)

        self.assertEqual(record["llm_cache"], llm_cache)
        self.assertIn("LLM Cache", html)
        self.assertIn("read-only", html)
        self.assertIn("artifacts/llm-cache", html)

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
        self.assertIn("Social Chronicle", html)
        self.assertIn("Historical Scar Validation", html)
        self.assertIn("Day 1", html)

    def test_run_html_renders_historical_scars(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.relationship_crises["a1|a2"] = 3
        simulation.world.blocked_routes["commons|north_field"] = 0.75
        simulation.world.organization_fractures["common_council"] = 4
        metrics = simulation.run(1)

        record = build_run_record(7, metrics, simulation.world, assess_metrics(metrics))
        html = render_run_html(record)

        self.assertIn("Historical Scars", html)
        self.assertIn("Historical Scar Validation", html)
        self.assertIn("relationship_crises_persist", html)
        self.assertIn("blocked_routes_affect_paths", html)
        self.assertIn("Relationship Crises", html)
        self.assertIn("Blocked Routes", html)
        self.assertIn("Organization Fractures", html)
        self.assertIn("commons|north_field", html)

    def test_run_html_renders_observer_intent_follow_through(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="broadcast",
                    params={
                        "intent": "repair_routes",
                        "target_agent_ids": ["a1"],
                        "message": "Reopen blocked routes.",
                    },
                )
            ],
        )
        simulation.world.agents[0].plan_history.append(
            "day 1: repair | observer intent emphasizes route repair"
        )

        record = build_run_record(7, metrics, simulation.world, assess_metrics(metrics))
        html = render_run_html(record)

        self.assertIn("Observer Intent Follow-through", html)
        self.assertIn("intent_memory_plan_echo", html)
        self.assertIn("repair_routes", html)

    def test_run_html_renders_choice_tension_evaluation(self) -> None:
        simulation = Simulation(seed=7)
        metrics = simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="broadcast",
                    params={
                        "intent": "repair_routes",
                        "target_agent_ids": ["a2"],
                        "message": "Reopen blocked routes.",
                    },
                )
            ],
        )
        cognition_trace = [
            {
                "day": 1,
                "agent_id": "a2",
                "agent_name": "Bo",
                "status": "primary",
                "baseline_plan": {
                    "action": "haul",
                    "reason": "food needs hauling to shared depots",
                },
                "proposed_plan": {
                    "action": "haul",
                    "reason": "Food pressure remains urgent, but blocked routes matter.",
                },
                "used_plan": {
                    "action": "haul",
                    "reason": "Food pressure remains urgent, but blocked routes matter.",
                },
            }
        ]

        record = build_run_record(
            7,
            metrics,
            simulation.world,
            assess_metrics(metrics),
            cognition_trace=cognition_trace,
        )
        html = render_run_html(record)

        self.assertIn("Choice Tension Evaluation", html)
        self.assertIn("choice_tension_baseline_aligned_with_tradeoff", html)
        self.assertIn("repair_routes", html)

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
