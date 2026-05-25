from __future__ import annotations

import argparse
import json

from .api import run_server
from .codex_cli_provider import (
    CodexCliCognition,
    CodexCliCognitionError,
    CodexCliDialogue,
    CodexCliReflection,
    resolve_codex_cli,
)
from .choice_tension_evaluation import assess_choice_tensions
from .cognition_impact_evaluation import assess_cognition_impacts
from .cognition_outcome_evaluation import assess_cognition_outcomes
from .counterfactual_evaluation import assess_counterfactual_trace
from .dialogue import HybridDialogue, HybridDialogueConfig
from .dialogue_evaluation import assess_dialogue_follow_through
from .experiment import run_experiment
from .generative_chain_evaluation import assess_generated_chains
from .health import assess_metrics
from .history import HistoryRecorder, write_snapshot_files
from .hybrid_cognition import HybridCognition, HybridCognitionConfig
from .interventions import load_interventions
from .llm_contract import build_cognition_context, render_plan_prompt
from .llm_cache import LLMCallCache
from .model import WorldState
from .openai_provider import OpenAICognition
from .reason_richness_evaluation import assess_reason_richness
from .reflection import HybridReflection, HybridReflectionConfig
from .reflection_evaluation import assess_reflection_follow_through
from .reports import (
    build_experiment_record,
    build_rule_baseline_comparison,
    build_run_record,
    render_experiment_html,
    render_run_html,
    write_html,
    write_json,
)
from .simulation import Simulation
from .social_evaluation import assess_social_dynamics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the virtual society simulation.")
    parser.add_argument("--days", type=int, default=30, help="Number of simulated days to run.")
    parser.add_argument("--seed", type=int, default=1, help="Deterministic simulation seed.")
    parser.add_argument(
        "--world-preset",
        choices=["base", "generative_alpha"],
        default="base",
        help="Initial world preset.",
    )
    parser.add_argument("--serve", action="store_true", help="Start the local HTTP API service.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for --serve.")
    parser.add_argument("--port", type=int, default=8765, help="Port for --serve.")
    parser.add_argument(
        "--report-every",
        type=int,
        default=1,
        help="Print one metrics row every N days.",
    )
    parser.add_argument(
        "--intervention-file",
        help="Path to a JSON list of scheduled observer interventions.",
    )
    parser.add_argument(
        "--experiment-seeds",
        help="Comma-separated seeds for a multi-seed long-run experiment.",
    )
    parser.add_argument("--show-plans", action="store_true", help="Print final active agent plans.")
    parser.add_argument(
        "--dump-cognition-context",
        help="Print the LLM-ready cognition context for an agent id after the run.",
    )
    parser.add_argument(
        "--codex-cli-plan-agent",
        help="Ask local Codex CLI for one plan for this agent id after the run.",
    )
    parser.add_argument("--codex-cli-path", help="Path to codex.exe. Defaults to ~/.codex/.sandbox-bin/codex.exe.")
    parser.add_argument("--codex-cli-model", default="gpt-5.4-mini", help="Codex CLI model for plan generation.")
    parser.add_argument("--codex-cli-timeout", type=int, default=180, help="Codex CLI timeout in seconds.")
    parser.add_argument("--llm-cache-dir", help="Directory for raw LLM prompt/response cache.")
    parser.add_argument(
        "--llm-cache-mode",
        choices=["off", "read-write", "read-only", "refresh"],
        default="off",
        help="LLM cache mode for generated providers.",
    )
    parser.add_argument(
        "--cognition",
        choices=["rule", "hybrid-codex-cli", "hybrid-openai"],
        default="rule",
        help="Cognition provider for the simulation loop.",
    )
    parser.add_argument("--llm-agent-ids", help="Comma-separated agent ids allowed to use the LLM provider.")
    parser.add_argument("--llm-every-days", type=int, default=7, help="Call LLM provider only on days divisible by N.")
    parser.add_argument("--llm-min-day", type=int, default=1, help="Earliest day allowed for LLM provider calls.")
    parser.add_argument("--llm-max-calls", type=int, default=1, help="Maximum LLM provider calls in one run.")
    parser.add_argument(
        "--llm-max-calls-per-day",
        type=int,
        default=0,
        help="Maximum LLM provider calls per simulated day. Use 0 for no daily cap.",
    )
    parser.add_argument("--llm-max-failures", type=int, default=1, help="Maximum LLM provider failures before fallback only.")
    parser.add_argument(
        "--llm-counterfactual-days",
        type=int,
        default=0,
        help="Short-horizon deterministic probe days before accepting a divergent LLM plan.",
    )
    parser.add_argument(
        "--llm-counterfactual-reject-threshold",
        type=float,
        default=0.02,
        help="Reject a divergent LLM plan when its probe score trails the rule baseline by more than this.",
    )
    parser.add_argument("--openai-model", default="gpt-5.2", help="OpenAI model for --cognition hybrid-openai.")
    parser.add_argument("--openai-timeout", type=int, default=60, help="OpenAI provider timeout in seconds.")
    parser.add_argument(
        "--openai-base-url",
        help="OpenAI-compatible base URL. Accepts either https://host/v1 or https://host/v1/responses.",
    )
    parser.add_argument(
        "--openai-reasoning-effort",
        default="",
        help="Optional Responses API reasoning effort, for example low or medium.",
    )
    parser.add_argument("--show-cognition-stats", action="store_true", help="Print cognition provider call stats.")
    parser.add_argument("--save-cognition-trace-json", help="Write hybrid cognition call trace JSON.")
    parser.add_argument(
        "--reflection",
        choices=["rule", "hybrid-codex-cli"],
        default="rule",
        help="Reflection provider for periodic agent reflections.",
    )
    parser.add_argument(
        "--reflection-agent-ids",
        help="Comma-separated agent ids allowed to use generated reflection.",
    )
    parser.add_argument(
        "--reflection-min-day",
        type=int,
        default=1,
        help="Earliest day allowed for generated reflection calls.",
    )
    parser.add_argument(
        "--reflection-max-calls",
        type=int,
        default=1,
        help="Maximum generated reflection calls in one run.",
    )
    parser.add_argument(
        "--reflection-max-failures",
        type=int,
        default=1,
        help="Maximum generated reflection failures before fallback only.",
    )
    parser.add_argument("--show-reflection-stats", action="store_true", help="Print reflection provider call stats.")
    parser.add_argument("--save-reflection-trace-json", help="Write hybrid reflection call trace JSON.")
    parser.add_argument(
        "--dialogue",
        choices=["rule", "hybrid-codex-cli"],
        default="rule",
        help="Dialogue provider for social actions.",
    )
    parser.add_argument(
        "--dialogue-agent-ids",
        help="Comma-separated speaker ids allowed to use generated dialogue.",
    )
    parser.add_argument(
        "--dialogue-min-day",
        type=int,
        default=1,
        help="Earliest day allowed for generated dialogue calls.",
    )
    parser.add_argument(
        "--dialogue-max-calls",
        type=int,
        default=1,
        help="Maximum generated dialogue calls in one run.",
    )
    parser.add_argument(
        "--dialogue-max-failures",
        type=int,
        default=1,
        help="Maximum generated dialogue failures before fallback only.",
    )
    parser.add_argument("--show-dialogue-stats", action="store_true", help="Print dialogue provider call stats.")
    parser.add_argument("--save-dialogue-trace-json", help="Write hybrid dialogue call trace JSON.")
    parser.add_argument(
        "--compare-rule-baseline",
        action="store_true",
        help="Run the same scenario with rule cognition and compare final metrics.",
    )
    parser.add_argument("--save-run-json", help="Write a JSON artifact for a single run.")
    parser.add_argument("--save-run-html", help="Write an offline HTML observer for a single run.")
    parser.add_argument(
        "--snapshot-every",
        type=int,
        default=0,
        help="Capture a read-only history snapshot every N days. Use 0 to disable.",
    )
    parser.add_argument(
        "--save-snapshots-dir",
        help="Write each captured history snapshot as a separate JSON file.",
    )
    parser.add_argument("--save-experiment-json", help="Write a JSON artifact for an experiment run.")
    parser.add_argument("--save-experiment-html", help="Write an offline HTML report for an experiment run.")
    parser.add_argument("--json", action="store_true", help="Print final snapshot as JSON.")
    args = parser.parse_args()

    if args.report_every < 1:
        raise SystemExit("--report-every must be >= 1")
    if args.snapshot_every < 0:
        raise SystemExit("--snapshot-every must be >= 0")
    if args.llm_counterfactual_days < 0:
        raise SystemExit("--llm-counterfactual-days must be >= 0")
    if args.llm_max_calls_per_day < 0:
        raise SystemExit("--llm-max-calls-per-day must be >= 0")
    if args.llm_counterfactual_reject_threshold < 0:
        raise SystemExit("--llm-counterfactual-reject-threshold must be >= 0")
    if args.llm_cache_mode != "off" and not args.llm_cache_dir:
        raise SystemExit("--llm-cache-dir is required when --llm-cache-mode is not off")
    if args.serve:
        run_server(
            seed=args.seed,
            host=args.host,
            port=args.port,
            snapshot_interval_days=args.snapshot_every or 30,
            world_preset=args.world_preset,
        )
        return

    interventions = load_interventions(args.intervention_file) if args.intervention_file else []

    if args.experiment_seeds:
        reports = run_experiment(
            seeds=_parse_seeds(args.experiment_seeds),
            days=args.days,
            interventions=interventions,
            world_preset=args.world_preset,
        )
        if args.save_experiment_json or args.save_experiment_html:
            experiment_record = build_experiment_record(reports)
            if args.save_experiment_json:
                write_json(args.save_experiment_json, experiment_record)
            if args.save_experiment_html:
                write_html(args.save_experiment_html, render_experiment_html(experiment_record))
        if args.json:
            print(json.dumps([report.as_dict() for report in reports], ensure_ascii=False, indent=2))
            return
        _print_experiment(reports)
        if args.save_experiment_json:
            print(f"\nSaved experiment JSON: {args.save_experiment_json}")
        if args.save_experiment_html:
            print(f"Saved experiment HTML: {args.save_experiment_html}")
        return

    cognition = _build_cognition(args)
    reflection = _build_reflection(args)
    dialogue = _build_dialogue(args)
    simulation = Simulation(
        seed=args.seed,
        cognition=cognition,
        reflection=reflection,
        dialogue=dialogue,
        world_preset=args.world_preset,
    )
    effective_snapshot_every = args.snapshot_every
    if args.save_snapshots_dir and effective_snapshot_every == 0:
        effective_snapshot_every = 30
    history_recorder = (
        HistoryRecorder(seed=args.seed, interval_days=effective_snapshot_every)
        if effective_snapshot_every
        else None
    )
    metrics = simulation.run(
        args.days,
        interventions=interventions,
        after_step=history_recorder.capture if history_recorder is not None else None,
    )
    if history_recorder is not None and metrics:
        history_recorder.capture(simulation.world, metrics[-1], force=True)
    history = history_recorder.record(metrics) if history_recorder is not None else None
    findings = assess_metrics(metrics)
    social_findings = assess_social_dynamics(simulation.world)
    cognition_trace = _cognition_trace(cognition)
    counterfactual_evaluation = assess_counterfactual_trace(cognition_trace).as_dict()
    reflection_trace = _reflection_trace(reflection)
    dialogue_trace = _dialogue_trace(dialogue)
    llm_cache = _llm_cache_summary(cognition, reflection, dialogue)
    baseline_comparison = None
    baseline_world = None
    baseline_metrics = None
    if args.compare_rule_baseline:
        baseline_comparison, baseline_world, baseline_metrics = _run_rule_baseline(
            args,
            interventions,
            metrics,
        )
    cognition_impacts = [
        item.as_dict()
        for item in assess_cognition_impacts(
            simulation.world,
            cognition_trace,
            baseline_world=baseline_world,
        )
    ]
    cognition_outcomes = [
        item.as_dict()
        for item in assess_cognition_outcomes(
            metrics,
            baseline_metrics,
            cognition_impacts,
        )
    ]
    choice_tensions = [
        item.as_dict()
        for item in assess_choice_tensions(simulation.world, cognition_trace)
    ]
    reason_richness = [
        item.as_dict()
        for item in assess_reason_richness(cognition_trace)
    ]
    reflection_follow_through = [
        item.as_dict()
        for item in assess_reflection_follow_through(
            simulation.world,
            reflection_trace,
            baseline_world=baseline_world,
        )
    ]
    dialogue_follow_through = [
        item.as_dict()
        for item in assess_dialogue_follow_through(
            simulation.world,
            dialogue_trace,
            baseline_world=baseline_world,
        )
    ]
    generated_chains = [
        item.as_dict()
        for item in assess_generated_chains(
            simulation.world,
            dialogue_trace,
            reflection_trace,
            baseline_world=baseline_world,
        )
    ]
    if args.save_run_json or args.save_run_html:
        run_record = build_run_record(
            args.seed,
            metrics,
            simulation.world,
            findings,
            history=history,
            cognition_trace=cognition_trace,
            counterfactual_evaluation=counterfactual_evaluation,
            cognition_impacts=cognition_impacts,
            cognition_outcomes=cognition_outcomes,
            reason_richness=reason_richness,
            reflection_trace=reflection_trace,
            reflection_follow_through=reflection_follow_through,
            dialogue_trace=dialogue_trace,
            dialogue_follow_through=dialogue_follow_through,
            generated_chains=generated_chains,
            llm_cache=llm_cache,
            baseline_comparison=baseline_comparison,
        )
        if args.save_run_json:
            write_json(args.save_run_json, run_record)
        if args.save_run_html:
            write_html(args.save_run_html, render_run_html(run_record))
    if args.save_cognition_trace_json:
        write_json(args.save_cognition_trace_json, cognition_trace)
    if args.save_reflection_trace_json:
        write_json(args.save_reflection_trace_json, reflection_trace)
    if args.save_dialogue_trace_json:
        write_json(args.save_dialogue_trace_json, dialogue_trace)
    if args.save_snapshots_dir and history_recorder is not None:
        write_snapshot_files(args.save_snapshots_dir, history_recorder.snapshots)

    if args.json:
        payload = simulation.snapshot()
        if history is not None:
            payload["history"] = history
        if baseline_comparison is not None:
            payload["baseline_comparison"] = baseline_comparison
        if cognition_impacts:
            payload["cognition_impacts"] = cognition_impacts
        if cognition_outcomes:
            payload["cognition_outcomes"] = cognition_outcomes
        if choice_tensions:
            payload["choice_tensions"] = choice_tensions
        if reason_richness:
            payload["reason_richness"] = reason_richness
        if counterfactual_evaluation["total"]:
            payload["counterfactual_evaluation"] = counterfactual_evaluation
        if reflection_follow_through:
            payload["reflection_follow_through"] = reflection_follow_through
        if dialogue_follow_through:
            payload["dialogue_follow_through"] = dialogue_follow_through
        if generated_chains:
            payload["generated_chains"] = generated_chains
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if interventions:
        print(
            f"Virtual society run | seed={args.seed} | days={args.days} | "
            f"interventions={len(interventions)}"
        )
    else:
        print(f"Virtual society run | seed={args.seed} | days={args.days}")
    _print_metrics(metrics, args.report_every)
    _print_findings(findings)
    _print_social_findings(social_findings)
    if args.show_plans:
        _print_plans(simulation)
    if args.dump_cognition_context:
        _print_cognition_context(simulation, args.dump_cognition_context)
    if args.codex_cli_plan_agent:
        _print_codex_cli_plan(simulation, args)
    if args.show_cognition_stats or isinstance(cognition, HybridCognition):
        _print_cognition_stats(cognition)
        _print_cognition_trace(cognition)
        _print_counterfactual_evaluation(counterfactual_evaluation)
        _print_cognition_impacts(cognition_impacts)
        _print_cognition_outcomes(cognition_outcomes)
        _print_choice_tensions(choice_tensions)
        _print_reason_richness(reason_richness)
    if args.show_reflection_stats or isinstance(reflection, HybridReflection):
        _print_reflection_stats(reflection)
        _print_reflection_trace(reflection)
        _print_reflection_follow_through(reflection_follow_through)
    if args.show_dialogue_stats or isinstance(dialogue, HybridDialogue):
        _print_dialogue_stats(dialogue)
        _print_dialogue_trace(dialogue)
        _print_dialogue_follow_through(dialogue_follow_through)
    if generated_chains:
        _print_generated_chains(generated_chains)
    if llm_cache:
        _print_llm_cache_summary(llm_cache)
    if baseline_comparison is not None:
        _print_baseline_comparison(baseline_comparison)
    if history is not None:
        _print_history(history)
    if args.save_run_json:
        print(f"\nSaved run JSON: {args.save_run_json}")
    if args.save_run_html:
        print(f"Saved run HTML: {args.save_run_html}")
    if args.save_cognition_trace_json:
        print(f"Saved cognition trace JSON: {args.save_cognition_trace_json}")
    if args.save_reflection_trace_json:
        print(f"Saved reflection trace JSON: {args.save_reflection_trace_json}")
    if args.save_dialogue_trace_json:
        print(f"Saved dialogue trace JSON: {args.save_dialogue_trace_json}")
    if args.save_snapshots_dir:
        print(f"Saved history snapshots: {args.save_snapshots_dir}")

    print("\nRecent events:")
    for event in simulation.world.event_log[-10:]:
        print(f"day {event.day:>3} | {event.kind:<17} | {event.description}")


def _print_metrics(metrics: list, report_every: int) -> None:
    print("day pop food materials shelter avg_need avg_trust avg_rep cohesion crises")
    for item in metrics:
        should_print = (
            item.day == 1
            or item.day == metrics[-1].day
            or item.day % report_every == 0
        )
        if not should_print:
            continue
        print(
            f"{item.day:>3} "
            f"{item.population:>3} "
            f"{item.food:>5.1f} "
            f"{item.materials:>9.1f} "
            f"{item.shelter:>7.1f} "
            f"{item.average_need:>8.3f} "
            f"{item.average_trust:>9.3f} "
            f"{item.average_reputation:>7.3f} "
            f"{item.institutional_cohesion:>8.3f} "
            f"{item.crisis_events:>6}"
        )


def _print_findings(findings: list) -> None:
    print("\nHealth findings:")
    for finding in findings:
        print(f"{finding.severity:<8} | {finding.code:<24} | {finding.description}")


def _print_social_findings(findings: list) -> None:
    print("\nSocial findings:")
    for finding in findings:
        print(f"{finding.severity:<8} | {finding.code:<24} | {finding.description}")


def _print_history(history: dict) -> None:
    print("\nHistory summary:")
    print(history["summary"])
    print(f"snapshots={history['snapshot_count']} interval_days={history['interval_days']}")


def _print_plans(simulation: Simulation) -> None:
    print("\nFinal active plans:")
    for agent in simulation.world.agents:
        if agent.active_plan is None:
            print(f"{agent.name:<8} | none")
            continue
        plan = agent.active_plan
        target = f" -> {plan.target_id}" if plan.target_id else ""
        print(
            f"{agent.name:<8} | {plan.action.value:<9}{target:<8} | "
            f"priority={plan.priority:.3f} | {plan.reason}"
        )


def _print_cognition_context(simulation: Simulation, agent_id: str) -> None:
    agent = next((candidate for candidate in simulation.world.agents if candidate.id == agent_id), None)
    if agent is None:
        raise SystemExit(f"Unknown agent id: {agent_id}")
    context = build_cognition_context(agent, simulation.world)
    print("\nLLM-ready cognition prompt:")
    print(render_plan_prompt(context))


def _print_codex_cli_plan(simulation: Simulation, args: argparse.Namespace) -> None:
    agent = _find_agent_or_exit(simulation, args.codex_cli_plan_agent)
    codex_path = args.codex_cli_path or resolve_codex_cli()
    provider = CodexCliCognition(
        codex_path=codex_path,
        model=args.codex_cli_model,
        reasoning_effort="low",
        timeout_seconds=args.codex_cli_timeout,
        workdir=".",
        cache=_build_llm_cache(args),
    )
    try:
        plan = provider.propose_plan(agent, simulation.world)
    except CodexCliCognitionError as exc:
        raise SystemExit(str(exc)) from exc

    print("\nCodex CLI proposed plan:")
    target = f" -> {plan.target_id}" if plan.target_id else ""
    print(
        f"{agent.name:<8} | {plan.action.value:<9}{target:<8} | "
        f"priority={plan.priority:.3f} | {plan.reason}"
    )


def _print_cognition_stats(cognition) -> None:
    if not isinstance(cognition, HybridCognition):
        print("\nCognition stats:")
        print("rule-based provider only")
        return
    stats = cognition.stats
    print("\nCognition stats:")
    print(
        f"llm_attempts={stats.llm_attempts} "
        f"llm_successes={stats.llm_successes} "
        f"llm_failures={stats.llm_failures} "
        f"fallback_calls={stats.fallback_calls} "
        f"skipped_calls={stats.skipped_calls}"
    )
    if stats.last_errors:
        print(f"last_error={stats.last_errors[-1]}")


def _print_cognition_trace(cognition) -> None:
    if not isinstance(cognition, HybridCognition) or not cognition.trace:
        return
    print("\nCognition trace:")
    print(_cognition_trace_summary(cognition))
    for item in cognition.trace[-5:]:
        proposed = item.proposed_plan or {}
        baseline = item.baseline_plan
        used = item.used_plan
        proposed_action = proposed.get("action", "none")
        print(
            f"day {item.day:>3} | {item.agent_name:<8} | {item.status:<20} | "
            f"primary={proposed_action:<9} rule={baseline['action']:<9} "
            f"used={used['action']:<9} diverged={item.diverged_from_baseline}"
        )
        if item.error:
            print(f"          error={item.error}")


def _print_cognition_impacts(impacts: list[dict]) -> None:
    if not impacts:
        return
    print("\nCognition impact:")
    for item in impacts[-5:]:
        print(
            f"day {item['day']:>3} | {item['agent_name']:<8} | "
            f"{item['signal']:<36} | {item['summary']}"
        )


def _print_counterfactual_evaluation(evaluation: dict) -> None:
    if not evaluation.get("total"):
        return
    print("\nCounterfactual evaluation:")
    print(evaluation.get("summary", "No counterfactual summary."))
    for item in (evaluation.get("by_action_pair") or [])[:5]:
        print(
            f"{item['label']:<18} | total={item['total']} "
            f"accepted={item['accepted']} rejected={item['rejected']} "
            f"avg_delta={_signed_number(item['average_score_delta'])}"
        )


def _print_cognition_outcomes(outcomes: list[dict]) -> None:
    if not outcomes:
        return
    print("\nCognition outcome:")
    for item in outcomes[-5:]:
        final = (item.get("windows") or [{}])[-1]
        deltas = final.get("deltas") or {}
        print(
            f"day {item['day']:>3} | {item['agent_name']:<8} | "
            f"{item['outcome_signal']:<36} | "
            f"need={_signed_number(deltas.get('average_need', 0))} "
            f"trust={_signed_number(deltas.get('average_trust', 0))} "
            f"food={_signed_number(deltas.get('food', 0))} "
            f"shelter={_signed_number(deltas.get('shelter', 0))}"
        )


def _print_choice_tensions(items: list[dict]) -> None:
    if not items:
        return
    print("\nChoice tension:")
    for item in items[-5:]:
        print(
            f"day {item['day']:>3} | {item['agent_name']:<8} | "
            f"{item['signal']:<48} | "
            f"baseline={item.get('baseline_action') or 'none'} "
            f"used={item.get('used_action') or 'none'} "
            f"competing={', '.join(item.get('competing_groups') or [])}"
        )


def _print_reason_richness(items: list[dict]) -> None:
    if not items:
        return
    print("\nReason richness:")
    for item in items[-5:]:
        print(
            f"day {item['day']:>3} | {item['agent_name']:<8} | "
            f"{item['signal']:<48} | "
            f"generated={item.get('generated_score', 0)} "
            f"baseline={item.get('baseline_score', 0)} "
            f"groups={', '.join(item.get('generated_groups') or [])}"
        )


def _print_reflection_stats(reflection) -> None:
    if not isinstance(reflection, HybridReflection):
        print("\nReflection stats:")
        print("rule-based provider only")
        return
    stats = reflection.stats
    print("\nReflection stats:")
    print(
        f"llm_attempts={stats.llm_attempts} "
        f"llm_successes={stats.llm_successes} "
        f"llm_failures={stats.llm_failures} "
        f"fallback_calls={stats.fallback_calls} "
        f"skipped_calls={stats.skipped_calls}"
    )
    if stats.last_errors:
        print(f"last_error={stats.last_errors[-1]}")


def _print_reflection_trace(reflection) -> None:
    if not isinstance(reflection, HybridReflection) or not reflection.trace:
        return
    print("\nReflection trace:")
    print(_reflection_trace_summary(reflection))
    for item in reflection.trace[-5:]:
        proposed = item.proposed_reflection or "none"
        refs = ",".join(str(ref) for ref in item.memory_refs) or "none"
        print(
            f"day {item.day:>3} | {item.agent_name:<8} | {item.status:<20} | "
            f"focus={item.focus:<8} refs={refs:<8} | {proposed}"
        )
        if item.error:
            print(f"          error={item.error}")


def _print_reflection_follow_through(follow_through: list[dict]) -> None:
    if not follow_through:
        return
    print("\nReflection follow-through:")
    for item in follow_through[-5:]:
        print(
            f"day {item['day']:>3} | {item['agent_name']:<8} | "
            f"{item['signal']:<24} | {item['summary']}"
        )


def _print_dialogue_stats(dialogue) -> None:
    if not isinstance(dialogue, HybridDialogue):
        print("\nDialogue stats:")
        print("rule-based provider only")
        return
    stats = dialogue.stats
    print("\nDialogue stats:")
    print(
        f"llm_attempts={stats.llm_attempts} "
        f"llm_successes={stats.llm_successes} "
        f"llm_failures={stats.llm_failures} "
        f"fallback_calls={stats.fallback_calls} "
        f"skipped_calls={stats.skipped_calls}"
    )
    if stats.last_errors:
        print(f"last_error={stats.last_errors[-1]}")


def _print_dialogue_trace(dialogue) -> None:
    if not isinstance(dialogue, HybridDialogue) or not dialogue.trace:
        return
    print("\nDialogue trace:")
    print(_dialogue_trace_summary(dialogue))
    for item in dialogue.trace[-5:]:
        proposed = item.proposed_dialogue or "none"
        refs = ",".join(str(ref) for ref in item.memory_refs) or "none"
        print(
            f"day {item.day:>3} | {item.speaker_name:<8} -> {item.partner_name:<8} | "
            f"{item.status:<20} | focus={item.focus:<12} refs={refs:<8} | {proposed}"
        )
        if item.error:
            print(f"          error={item.error}")


def _print_dialogue_follow_through(follow_through: list[dict]) -> None:
    if not follow_through:
        return
    print("\nDialogue follow-through:")
    for item in follow_through[-5:]:
        print(
            f"day {item['day']:>3} | {item['speaker_name']:<8} -> "
            f"{item['partner_name']:<8} | {item['signal']:<34} | {item['summary']}"
        )


def _print_generated_chains(chains: list[dict]) -> None:
    print("\nGenerated chains:")
    for item in chains[-5:]:
        print(
            f"dialogue day {item['dialogue_day']:>3} -> reflection day "
            f"{item['reflection_day']:>3} | {item['reflection_agent_name']:<8} | "
            f"{item['signal']:<38} | {item['summary']}"
        )


def _print_llm_cache_summary(items: list[dict]) -> None:
    print("\nLLM cache:")
    for item in items:
        print(
            f"{item['surface']:<10} | mode={item['mode']:<10} "
            f"reads={item['reads']} hits={item['hits']} "
            f"misses={item['misses']} writes={item['writes']} | "
            f"{item['root_dir']}"
        )


def _print_baseline_comparison(comparison: dict) -> None:
    print("\nRule baseline comparison:")
    print(comparison.get("summary", "No comparison summary."))
    deltas = comparison.get("deltas", {})
    for key in (
        "average_need",
        "average_trust",
        "institutional_cohesion",
        "food",
        "materials",
        "shelter",
        "crisis_events",
    ):
        if key in deltas:
            print(f"{key:<24} {_signed_number(deltas[key])}")


def _run_rule_baseline(
    args: argparse.Namespace,
    interventions: list,
    metrics: list,
) -> tuple[dict, WorldState, list]:
    baseline = Simulation(seed=args.seed, world_preset=args.world_preset)
    baseline_metrics = baseline.run(args.days, interventions=interventions)
    baseline_findings = assess_metrics(baseline_metrics)
    baseline_social_findings = assess_social_dynamics(baseline.world)
    return (
        build_rule_baseline_comparison(
            metrics,
            baseline_metrics,
            baseline_findings,
            baseline_social_findings,
        ),
        baseline.world,
        baseline_metrics,
    )


def _cognition_trace(cognition) -> list[dict]:
    if not isinstance(cognition, HybridCognition):
        return []
    return [item.as_dict() for item in cognition.trace]


def _reflection_trace(reflection) -> list[dict]:
    if not isinstance(reflection, HybridReflection):
        return []
    return [item.as_dict() for item in reflection.trace]


def _dialogue_trace(dialogue) -> list[dict]:
    if not isinstance(dialogue, HybridDialogue):
        return []
    return [item.as_dict() for item in dialogue.trace]


def _llm_cache_summary(cognition, reflection, dialogue) -> list[dict]:
    items = []
    for surface, provider in (
        ("cognition", cognition),
        ("reflection", reflection),
        ("dialogue", dialogue),
    ):
        primary = getattr(provider, "primary", provider)
        cache = getattr(primary, "cache", None)
        if cache is None:
            continue
        stats = cache.stats
        items.append(
            {
                "surface": surface,
                "provider": cache.provider,
                "mode": cache.mode,
                "root_dir": str(cache.root_dir),
                "model": getattr(primary, "model", ""),
                "reasoning_effort": getattr(primary, "reasoning_effort", ""),
                "reads": stats.reads,
                "hits": stats.hits,
                "misses": stats.misses,
                "writes": stats.writes,
            }
        )
    return items


def _cognition_trace_summary(cognition: HybridCognition) -> str:
    calls = len(cognition.trace)
    accepted = sum(1 for item in cognition.trace if item.status == "primary")
    policy_fallbacks = sum(
        1
        for item in cognition.trace
        if item.status in {"baseline_after_policy", "baseline_after_counterfactual"}
    )
    failures = calls - accepted - policy_fallbacks
    diverged = sum(1 for item in cognition.trace if item.diverged_from_baseline)
    rest_overrides = sum(
        1
        for item in cognition.trace
        if item.used_plan["action"] == "rest"
        and item.baseline_plan["action"] != "rest"
    )
    divergence_rate = diverged / calls if calls else 0.0
    return (
        f"calls={calls} accepted={accepted} policy_fallbacks={policy_fallbacks} "
        f"failures={failures} divergence_rate={divergence_rate:.0%} "
        f"rest_overrides={rest_overrides}"
    )


def _reflection_trace_summary(reflection: HybridReflection) -> str:
    calls = len(reflection.trace)
    accepted = sum(1 for item in reflection.trace if item.status == "primary")
    failures = calls - accepted
    cited = sum(1 for item in reflection.trace if item.memory_refs)
    return (
        f"calls={calls} accepted={accepted} failures={failures} "
        f"memory_grounded={cited}"
    )


def _dialogue_trace_summary(dialogue: HybridDialogue) -> str:
    calls = len(dialogue.trace)
    accepted = sum(1 for item in dialogue.trace if item.status == "primary")
    failures = calls - accepted
    cited = sum(1 for item in dialogue.trace if item.memory_refs)
    return (
        f"calls={calls} accepted={accepted} failures={failures} "
        f"memory_grounded={cited}"
    )


def _signed_number(value: float) -> str:
    number = float(value)
    if number > 0:
        return f"+{number:g}"
    return f"{number:g}"


def _find_agent_or_exit(simulation: Simulation, agent_id: str):
    agent = next((candidate for candidate in simulation.world.agents if candidate.id == agent_id), None)
    if agent is None:
        raise SystemExit(f"Unknown agent id: {agent_id}")
    return agent


def _print_experiment(reports: list) -> None:
    print("Virtual society experiment")
    print("seed days pop food materials shelter avg_need avg_trust avg_rep cohesion findings")
    for report in reports:
        final = report.final_metrics
        codes = ",".join(finding.code for finding in report.findings)
        print(
            f"{report.seed:>4} "
            f"{report.days:>4} "
            f"{final.population:>3} "
            f"{final.food:>5.1f} "
            f"{final.materials:>9.1f} "
            f"{final.shelter:>7.1f} "
            f"{final.average_need:>8.3f} "
            f"{final.average_trust:>9.3f} "
            f"{final.average_reputation:>7.3f} "
            f"{final.institutional_cohesion:>8.3f} "
            f"{codes}"
        )


def _parse_seeds(value: str) -> list[int]:
    seeds = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not seeds:
        raise ValueError("--experiment-seeds must contain at least one seed")
    return seeds


def _build_cognition(args: argparse.Namespace):
    if args.cognition == "rule":
        return None

    if args.cognition == "hybrid-codex-cli":
        cache = _build_llm_cache(args, provider="codex-cli")
        primary = CodexCliCognition(
            codex_path=args.codex_cli_path or resolve_codex_cli(),
            model=args.codex_cli_model,
            reasoning_effort="low",
            timeout_seconds=args.codex_cli_timeout,
            workdir=".",
            cache=cache,
        )
        return HybridCognition(
            primary=primary,
            config=HybridCognitionConfig(
                agent_ids=_parse_optional_agent_ids(args.llm_agent_ids),
                every_days=args.llm_every_days,
                min_day=args.llm_min_day,
                max_calls=args.llm_max_calls,
                max_calls_per_day=args.llm_max_calls_per_day,
                max_failures=args.llm_max_failures,
                counterfactual_horizon_days=args.llm_counterfactual_days,
                counterfactual_reject_threshold=args.llm_counterfactual_reject_threshold,
            ),
        )

    if args.cognition == "hybrid-openai":
        cache = _build_llm_cache(args, provider="openai-compatible")
        primary = OpenAICognition(
            model=args.openai_model,
            timeout_seconds=args.openai_timeout,
            base_url=args.openai_base_url,
            reasoning_effort=args.openai_reasoning_effort,
            cache=cache,
        )
        return HybridCognition(
            primary=primary,
            config=HybridCognitionConfig(
                agent_ids=_parse_optional_agent_ids(args.llm_agent_ids),
                every_days=args.llm_every_days,
                min_day=args.llm_min_day,
                max_calls=args.llm_max_calls,
                max_calls_per_day=args.llm_max_calls_per_day,
                max_failures=args.llm_max_failures,
                counterfactual_horizon_days=args.llm_counterfactual_days,
                counterfactual_reject_threshold=args.llm_counterfactual_reject_threshold,
            ),
        )

    raise ValueError(f"Unknown cognition provider: {args.cognition}")


def _build_reflection(args: argparse.Namespace):
    if args.reflection == "rule":
        return None

    cache = _build_llm_cache(args, provider="codex-cli")
    if args.reflection == "hybrid-codex-cli":
        primary = CodexCliReflection(
            codex_path=args.codex_cli_path or resolve_codex_cli(),
            model=args.codex_cli_model,
            reasoning_effort="low",
            timeout_seconds=args.codex_cli_timeout,
            workdir=".",
            cache=cache,
        )
        return HybridReflection(
            primary=primary,
            config=HybridReflectionConfig(
                agent_ids=_parse_optional_agent_ids(args.reflection_agent_ids),
                min_day=args.reflection_min_day,
                max_calls=args.reflection_max_calls,
                max_failures=args.reflection_max_failures,
            ),
        )

    raise ValueError(f"Unknown reflection provider: {args.reflection}")


def _build_dialogue(args: argparse.Namespace):
    if args.dialogue == "rule":
        return None

    cache = _build_llm_cache(args, provider="codex-cli")
    if args.dialogue == "hybrid-codex-cli":
        primary = CodexCliDialogue(
            codex_path=args.codex_cli_path or resolve_codex_cli(),
            model=args.codex_cli_model,
            reasoning_effort="low",
            timeout_seconds=args.codex_cli_timeout,
            workdir=".",
            cache=cache,
        )
        return HybridDialogue(
            primary=primary,
            config=HybridDialogueConfig(
                agent_ids=_parse_optional_agent_ids(args.dialogue_agent_ids),
                min_day=args.dialogue_min_day,
                max_calls=args.dialogue_max_calls,
                max_failures=args.dialogue_max_failures,
            ),
        )

    raise ValueError(f"Unknown dialogue provider: {args.dialogue}")


def _build_llm_cache(args: argparse.Namespace, provider: str = "codex-cli") -> LLMCallCache | None:
    if args.llm_cache_mode == "off":
        return None
    if not args.llm_cache_dir:
        raise SystemExit("--llm-cache-dir is required when --llm-cache-mode is not off")
    return LLMCallCache(args.llm_cache_dir, mode=args.llm_cache_mode, provider=provider)


def _parse_optional_agent_ids(value: str | None) -> set[str] | None:
    if not value:
        return None
    ids = {item.strip() for item in value.split(",") if item.strip()}
    if not ids:
        return None
    return ids


if __name__ == "__main__":
    main()
