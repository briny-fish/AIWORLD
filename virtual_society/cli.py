from __future__ import annotations

import argparse
import json

from .api import run_server
from .codex_cli_provider import CodexCliCognition, CodexCliCognitionError, resolve_codex_cli
from .experiment import run_experiment
from .health import assess_metrics
from .history import HistoryRecorder, write_snapshot_files
from .hybrid_cognition import HybridCognition, HybridCognitionConfig
from .interventions import load_interventions
from .llm_contract import build_cognition_context, render_plan_prompt
from .openai_provider import OpenAICognition
from .reports import (
    build_experiment_record,
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
    parser.add_argument("--llm-max-failures", type=int, default=1, help="Maximum LLM provider failures before fallback only.")
    parser.add_argument("--openai-model", default="gpt-5.2", help="OpenAI model for --cognition hybrid-openai.")
    parser.add_argument("--openai-timeout", type=int, default=60, help="OpenAI provider timeout in seconds.")
    parser.add_argument("--show-cognition-stats", action="store_true", help="Print cognition provider call stats.")
    parser.add_argument("--save-cognition-trace-json", help="Write hybrid cognition call trace JSON.")
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
    simulation = Simulation(seed=args.seed, cognition=cognition, world_preset=args.world_preset)
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
    if args.save_run_json or args.save_run_html:
        run_record = build_run_record(
            args.seed,
            metrics,
            simulation.world,
            findings,
            history=history,
            cognition_trace=cognition_trace,
        )
        if args.save_run_json:
            write_json(args.save_run_json, run_record)
        if args.save_run_html:
            write_html(args.save_run_html, render_run_html(run_record))
    if args.save_cognition_trace_json:
        write_json(args.save_cognition_trace_json, cognition_trace)
    if args.save_snapshots_dir and history_recorder is not None:
        write_snapshot_files(args.save_snapshots_dir, history_recorder.snapshots)

    if args.json:
        payload = simulation.snapshot()
        if history is not None:
            payload["history"] = history
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
    if history is not None:
        _print_history(history)
    if args.save_run_json:
        print(f"\nSaved run JSON: {args.save_run_json}")
    if args.save_run_html:
        print(f"Saved run HTML: {args.save_run_html}")
    if args.save_cognition_trace_json:
        print(f"Saved cognition trace JSON: {args.save_cognition_trace_json}")
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
            f"codex={proposed_action:<9} rule={baseline['action']:<9} "
            f"used={used['action']:<9} diverged={item.diverged_from_baseline}"
        )
        if item.error:
            print(f"          error={item.error}")


def _cognition_trace(cognition) -> list[dict]:
    if not isinstance(cognition, HybridCognition):
        return []
    return [item.as_dict() for item in cognition.trace]


def _cognition_trace_summary(cognition: HybridCognition) -> str:
    calls = len(cognition.trace)
    successes = sum(1 for item in cognition.trace if item.status == "primary")
    failures = calls - successes
    diverged = sum(1 for item in cognition.trace if item.diverged_from_baseline)
    rest_overrides = sum(
        1
        for item in cognition.trace
        if item.used_plan["action"] == "rest"
        and item.baseline_plan["action"] != "rest"
    )
    divergence_rate = diverged / calls if calls else 0.0
    return (
        f"calls={calls} successes={successes} failures={failures} "
        f"divergence_rate={divergence_rate:.0%} rest_overrides={rest_overrides}"
    )


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
        primary = CodexCliCognition(
            codex_path=args.codex_cli_path or resolve_codex_cli(),
            model=args.codex_cli_model,
            reasoning_effort="low",
            timeout_seconds=args.codex_cli_timeout,
            workdir=".",
        )
        return HybridCognition(
            primary=primary,
            config=HybridCognitionConfig(
                agent_ids=_parse_optional_agent_ids(args.llm_agent_ids),
                every_days=args.llm_every_days,
                min_day=args.llm_min_day,
                max_calls=args.llm_max_calls,
                max_failures=args.llm_max_failures,
            ),
        )

    if args.cognition == "hybrid-openai":
        primary = OpenAICognition(
            model=args.openai_model,
            timeout_seconds=args.openai_timeout,
        )
        return HybridCognition(
            primary=primary,
            config=HybridCognitionConfig(
                agent_ids=_parse_optional_agent_ids(args.llm_agent_ids),
                every_days=args.llm_every_days,
                min_day=args.llm_min_day,
                max_calls=args.llm_max_calls,
                max_failures=args.llm_max_failures,
            ),
        )

    raise ValueError(f"Unknown cognition provider: {args.cognition}")


def _parse_optional_agent_ids(value: str | None) -> set[str] | None:
    if not value:
        return None
    ids = {item.strip() for item in value.split(",") if item.strip()}
    if not ids:
        return None
    return ids


if __name__ == "__main__":
    main()
