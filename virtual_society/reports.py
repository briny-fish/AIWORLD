from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from .agent_dossiers import build_agent_record, build_relationship_links
from .choice_tension_evaluation import assess_choice_tensions
from .health import HealthFinding, RunReport
from .historical_scars import build_historical_scar_validation
from .model import Metrics, WorldState
from .observer_intent_evaluation import assess_observer_intents
from .observer_recommendations import build_observer_recommendations
from .reason_richness_evaluation import assess_reason_richness
from .scar_diagnosis import assess_scar_bottlenecks
from .social_evaluation import SocialFinding, assess_social_dynamics
from .social_chronicle import build_social_chronicle
from .social_timeline import build_influence_chains, build_social_feed


COMPARISON_METRICS = [
    "population",
    "food",
    "materials",
    "shelter",
    "average_need",
    "average_trust",
    "average_reputation",
    "institutional_cohesion",
    "crisis_events",
]


def build_run_record(
    seed: int,
    metrics: list[Metrics],
    world: WorldState,
    findings: list[HealthFinding],
    history: dict[str, Any] | None = None,
    cognition_trace: list[dict[str, Any]] | None = None,
    counterfactual_evaluation: dict[str, Any] | None = None,
    cognition_impacts: list[dict[str, Any]] | None = None,
    cognition_outcomes: list[dict[str, Any]] | None = None,
    reason_richness: list[dict[str, Any]] | None = None,
    reflection_trace: list[dict[str, Any]] | None = None,
    reflection_follow_through: list[dict[str, Any]] | None = None,
    dialogue_trace: list[dict[str, Any]] | None = None,
    dialogue_follow_through: list[dict[str, Any]] | None = None,
    generated_chains: list[dict[str, Any]] | None = None,
    llm_cache: list[dict[str, Any]] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    social_findings = assess_social_dynamics(world)
    social_finding_dicts = [item.as_dict() for item in social_findings]
    observer_intents = [item.as_dict() for item in assess_observer_intents(world)]
    choice_tensions = [
        item.as_dict()
        for item in assess_choice_tensions(world, cognition_trace or [])
    ]
    reason_richness_items = reason_richness or [
        item.as_dict()
        for item in assess_reason_richness(cognition_trace or [])
    ]
    social_chronicle = build_social_chronicle(
        history,
        social_finding_dicts,
        observer_intents,
    )
    scar_diagnosis = [
        item.as_dict()
        for item in assess_scar_bottlenecks(world, cognition_trace or [])
    ]
    observer_recommendations = [
        item.as_dict()
        for item in build_observer_recommendations(world, scar_diagnosis)
    ]
    dialogue_trace_items = dialogue_trace or []
    generated_chain_items = generated_chains or []
    story_cards = _story_cards(
        social_chronicle=social_chronicle,
        cognition_trace=cognition_trace or [],
        generated_chains=generated_chain_items,
        counterfactual_evaluation=counterfactual_evaluation,
        reason_richness=reason_richness_items,
        baseline_comparison=baseline_comparison,
    )
    relationship_links = build_relationship_links(world)
    agent_records = [build_agent_record(agent) for agent in world.agents]
    record = {
        "kind": "run",
        "generated_at": _now(),
        "seed": seed,
        "days": metrics[-1].day if metrics else world.day,
        "metrics": [asdict(item) for item in metrics],
        "final_metrics": asdict(metrics[-1]) if metrics else None,
        "findings": [asdict(item) for item in findings],
        "social_findings": social_finding_dicts,
        "resources": dict(world.resources),
        "route_loads": {
            key: round(value, 3)
            for key, value in world.route_loads.items()
        },
        "historical_scars": _historical_scars(world),
        "relationship_links": relationship_links,
        "historical_scar_validation": build_historical_scar_validation(world, history),
        "scar_diagnosis": scar_diagnosis,
        "story_cards": story_cards,
        "social_chronicle": social_chronicle,
        "social_feed": build_social_feed(
            world,
            dialogue_trace=dialogue_trace_items,
            generated_chains=generated_chain_items,
            limit=120,
        ),
        "influence_chains": build_influence_chains(
            world,
            generated_chains=generated_chain_items,
            limit=20,
        ),
        "observer_intents": observer_intents,
        "observer_memory": _observer_memory(world),
        "observer_recommendations": observer_recommendations,
        "choice_tensions": choice_tensions,
        "reason_richness": reason_richness_items,
        "agents": agent_records,
        "organizations": [
            {
                "id": organization.id,
                "name": organization.name,
                "kind": organization.kind,
                "home_location_id": organization.home_location_id,
                "members": list(organization.members),
                "norms": list(organization.norms),
                "inventory_targets": {
                    key: round(value, 3)
                    for key, value in organization.inventory_targets.items()
                },
                "exchange_preferences": {
                    key: round(value, 3)
                    for key, value in organization.exchange_preferences.items()
                },
                "cohesion": round(organization.cohesion, 3),
                "reputation": round(organization.reputation, 3),
            }
            for organization in world.organizations
        ],
        "locations": [
            {
                "id": location.id,
                "name": location.name,
                "kind": location.kind,
                "condition": round(location.condition, 3),
                "capacity": location.capacity,
                "production": {
                    key: round(value, 3)
                    for key, value in location.production.items()
                },
                "maintenance_need": round(location.maintenance_need, 3),
                "resources": {
                    key: round(value, 3)
                    for key, value in location.resources.items()
                },
                "connected_location_ids": list(location.connected_location_ids),
                "blocked_connected_location_ids": [
                    neighbor_id
                    for neighbor_id in location.connected_location_ids
                    if _route_key(location.id, neighbor_id) in world.blocked_routes
                ],
            }
            for location in world.locations
        ],
        "events": [asdict(event) for event in world.event_log],
    }
    if history is not None:
        record["history"] = history
    if cognition_trace is not None:
        record["cognition_trace"] = cognition_trace
    if counterfactual_evaluation is not None:
        record["counterfactual_evaluation"] = counterfactual_evaluation
    if cognition_impacts is not None:
        record["cognition_impacts"] = cognition_impacts
    if cognition_outcomes is not None:
        record["cognition_outcomes"] = cognition_outcomes
    if reflection_trace is not None:
        record["reflection_trace"] = reflection_trace
    if reflection_follow_through is not None:
        record["reflection_follow_through"] = reflection_follow_through
    if dialogue_trace is not None:
        record["dialogue_trace"] = dialogue_trace
    if dialogue_follow_through is not None:
        record["dialogue_follow_through"] = dialogue_follow_through
    if generated_chains is not None:
        record["generated_chains"] = generated_chains
    if llm_cache is not None:
        record["llm_cache"] = llm_cache
    if baseline_comparison is not None:
        record["baseline_comparison"] = baseline_comparison
    record["run_diagnosis"] = _run_diagnosis(record)
    return record


def build_rule_baseline_comparison(
    metrics: list[Metrics],
    baseline_metrics: list[Metrics],
    baseline_findings: list[HealthFinding],
    baseline_social_findings: list[SocialFinding],
) -> dict[str, Any]:
    if not metrics or not baseline_metrics:
        return {
            "kind": "rule_baseline",
            "summary": "Comparison unavailable because one run produced no metrics.",
            "final_metrics": None,
            "baseline_final_metrics": None,
            "deltas": {},
            "baseline_findings": [asdict(item) for item in baseline_findings],
            "baseline_social_findings": [
                item.as_dict()
                for item in baseline_social_findings
            ],
        }

    final = asdict(metrics[-1])
    baseline_final = asdict(baseline_metrics[-1])
    deltas = {
        key: round(float(final[key]) - float(baseline_final[key]), 3)
        for key in COMPARISON_METRICS
        if key in final and key in baseline_final
    }
    return {
        "kind": "rule_baseline",
        "summary": _comparison_summary(deltas),
        "final_metrics": final,
        "baseline_final_metrics": baseline_final,
        "deltas": deltas,
        "baseline_findings": [asdict(item) for item in baseline_findings],
        "baseline_social_findings": [
            item.as_dict()
            for item in baseline_social_findings
        ],
    }


def build_experiment_record(reports: list[RunReport]) -> dict[str, Any]:
    return {
        "kind": "experiment",
        "generated_at": _now(),
        "reports": [report.as_dict() for report in reports],
    }


def build_run_batch_record(run_records: list[dict[str, Any]]) -> dict[str, Any]:
    runs = [_run_batch_summary(record) for record in run_records]
    aggregate = _run_batch_aggregate(runs)
    return {
        "kind": "run_batch",
        "generated_at": _now(),
        "run_count": len(runs),
        "aggregate": aggregate,
        "runs": runs,
        "story_cards": _run_batch_story_cards(aggregate),
    }


def write_json(path: str | Path, data: dict[str, Any] | list[Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html(path: str | Path, html: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_strip_trailing_whitespace(html), encoding="utf-8")


def _strip_trailing_whitespace(html: str) -> str:
    lines = html.splitlines()
    output = "\n".join(line.rstrip() for line in lines)
    if html.endswith(("\n", "\r\n")):
        output += "\n"
    return output


def render_run_html(record: dict[str, Any]) -> str:
    metrics = record["metrics"]
    final = record["final_metrics"] or {}
    findings = record["findings"]
    social_findings = record.get("social_findings", [])
    cognition_trace = record.get("cognition_trace", [])
    counterfactual_evaluation = record.get("counterfactual_evaluation")
    cognition_impacts = record.get("cognition_impacts", [])
    cognition_outcomes = record.get("cognition_outcomes", [])
    choice_tensions = record.get("choice_tensions", [])
    reason_richness = record.get("reason_richness", [])
    reflection_trace = record.get("reflection_trace", [])
    reflection_follow_through = record.get("reflection_follow_through", [])
    dialogue_trace = record.get("dialogue_trace", [])
    dialogue_follow_through = record.get("dialogue_follow_through", [])
    generated_chains = record.get("generated_chains", [])
    run_diagnosis = record.get("run_diagnosis", [])
    llm_cache = record.get("llm_cache", [])
    baseline_comparison = record.get("baseline_comparison")
    story_cards = record.get("story_cards", [])
    agents = record["agents"]
    organizations = record.get("organizations", [])
    locations = record.get("locations", [])
    history = record.get("history")
    social_chronicle = record.get("social_chronicle")
    observer_intents = record.get("observer_intents", [])
    observer_memory = record.get("observer_memory", [])
    observer_recommendations = record.get("observer_recommendations", [])
    historical_scar_validation = record.get("historical_scar_validation")
    scar_diagnosis = record.get("scar_diagnosis", [])
    historical_scars = record.get("historical_scars", {})
    events = record["events"][-80:]
    title = f"Virtual Society Run | seed {record['seed']} | day {record['days']}"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  {_style()}
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <h1>Virtual Society Run</h1>
        <p>seed {record['seed']} · day {record['days']} · generated {escape(record['generated_at'])}</p>
      </div>
      <div class="status">{escape(_finding_summary(findings))}</div>
    </header>
    <section class="metric-strip">
      {_metric_tile("Population", final.get("population"))}
      {_metric_tile("Food", final.get("food"))}
      {_metric_tile("Materials", final.get("materials"))}
      {_metric_tile("Shelter", final.get("shelter"))}
      {_metric_tile("Avg Need", final.get("average_need"))}
      {_metric_tile("Avg Trust", final.get("average_trust"))}
      {_metric_tile("Avg Reputation", final.get("average_reputation"))}
      {_metric_tile("Org Cohesion", final.get("institutional_cohesion"))}
    </section>
    {_world_dashboard_section(record)}
    {_agent_dossiers_section(record)}
    {_story_cards_section(story_cards)}
    {_run_diagnosis_section(run_diagnosis)}
    <section class="band">
      <h2>Health</h2>
      <div class="finding-row">{''.join(_finding_badge(item) for item in findings)}</div>
    </section>
    <section class="band">
      <h2>Social Evaluation</h2>
      <div class="finding-row">{''.join(_social_finding_badge(item) for item in social_findings)}</div>
    </section>
    {_llm_cache_section(llm_cache)}
    {_counterfactual_evaluation_section(counterfactual_evaluation)}
    {_cognition_trace_section(cognition_trace)}
    {_cognition_impacts_section(cognition_impacts)}
    {_cognition_outcomes_section(cognition_outcomes)}
    {_choice_tension_section(choice_tensions)}
    {_reason_richness_section(reason_richness)}
    {_reflection_trace_section(reflection_trace)}
    {_reflection_follow_through_section(reflection_follow_through)}
    {_dialogue_trace_section(dialogue_trace)}
    {_dialogue_follow_through_section(dialogue_follow_through)}
    {_generated_chains_section(generated_chains)}
    {_baseline_comparison_section(baseline_comparison)}
    {_history_section(history)}
    {_social_chronicle_section(social_chronicle)}
    {_observer_recommendations_section(observer_recommendations)}
    {_observer_intent_section(observer_intents)}
    {_observer_memory_section(observer_memory)}
    {_scar_diagnosis_section(scar_diagnosis)}
    {_historical_scar_validation_section(historical_scar_validation)}
    {_historical_scars_section(historical_scars)}
    <section class="band">
      <h2>Metrics</h2>
      {_metrics_chart(metrics)}
    </section>
    <section class="band">
      <h2>Organizations</h2>
      {_organizations_table(organizations)}
    </section>
    <section class="band">
      <h2>Locations</h2>
      {_locations_table(locations)}
    </section>
    <section class="split">
      <div class="band">
        <h2>Agents</h2>
        {_agents_table(agents)}
      </div>
      <div class="band">
        <h2>Recent Events</h2>
        {_events_table(events)}
      </div>
    </section>
  </main>
</body>
</html>"""


def render_experiment_html(record: dict[str, Any]) -> str:
    reports = record["reports"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Virtual Society Experiment</title>
  {_style()}
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <h1>Virtual Society Experiment</h1>
        <p>{len(reports)} seeds · generated {escape(record['generated_at'])}</p>
      </div>
      <div class="status">{escape(_experiment_summary(reports))}</div>
    </header>
    <section class="band">
      <h2>Seed Comparison</h2>
      {_experiment_table(reports)}
    </section>
  </main>
</body>
</html>"""


def render_run_batch_html(record: dict[str, Any]) -> str:
    aggregate = record.get("aggregate", {})
    runs = record.get("runs", [])
    cards = record.get("story_cards", [])
    title = f"Virtual Society LLM Batch | {record.get('run_count', 0)} runs"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  {_style()}
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <h1>Virtual Society LLM Batch</h1>
        <p>{record.get('run_count', 0)} runs 路 generated {escape(record.get('generated_at', ''))}</p>
      </div>
      <div class="status">{escape(_run_batch_status(aggregate))}</div>
    </header>
    <section class="metric-strip">
      {_metric_tile("Runs", record.get("run_count", 0))}
      {_metric_tile("LLM Calls", aggregate.get("total_cognition_calls", 0))}
      {_metric_tile("Behavior Divergence", _percent(aggregate.get("behavior_divergence_rate", 0)))}
      {_metric_tile("Gate Acceptance", _percent(aggregate.get("counterfactual_acceptance_rate", 0)))}
      {_metric_tile("Avg Need Delta", _signed_number(aggregate.get("average_deltas", {}).get("average_need", 0)))}
      {_metric_tile("Avg Trust Delta", _signed_number(aggregate.get("average_deltas", {}).get("average_trust", 0)))}
      {_metric_tile("Avg Crisis Delta", _signed_number(aggregate.get("average_deltas", {}).get("crisis_events", 0)))}
      {_metric_tile("Richer Reasons", aggregate.get("richer_reason_count", 0))}
    </section>
    {_story_cards_section(cards)}
    <section class="band">
      <h2>Run Comparison</h2>
      {_run_batch_table(runs)}
    </section>
    <section class="band">
      <h2>Average Baseline Deltas</h2>
      {_baseline_delta_table(aggregate.get("average_deltas", {}))}
    </section>
  </main>
</body>
</html>"""


def _style() -> str:
    return """<style>
:root {
  color-scheme: light;
  --bg: #f5f7f7;
  --ink: #17201f;
  --muted: #596867;
  --line: #c8d1cf;
  --panel: #ffffff;
  --good: #23785f;
  --warn: #a15c12;
  --bad: #a33232;
  --blue: #2f5d86;
  --violet: #6e5792;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
  line-height: 1.45;
}
.shell { max-width: 1280px; margin: 0 auto; padding: 24px; }
.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 16px;
}
h1, h2, h3 { margin: 0; letter-spacing: 0; }
h1 { font-size: clamp(28px, 4vw, 48px); line-height: 1; }
h2 { font-size: 18px; margin-bottom: 12px; }
h3 { font-size: 14px; margin: 12px 0 8px; }
p { margin: 8px 0 0; color: var(--muted); }
.status {
  min-width: 220px;
  text-align: right;
  font-weight: 700;
  color: var(--blue);
}
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin: 18px 0;
}
.metric {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px;
  min-height: 80px;
}
.metric label { display: block; color: var(--muted); font-size: 12px; }
.metric strong { display: block; font-size: 28px; margin-top: 6px; }
.story-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
  margin: 12px 0;
}
.story-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 14px;
  min-height: 150px;
}
.story-card h3 { font-size: 15px; margin: 0 0 8px; }
.story-card p { margin: 6px 0; }
.story-card .evidence { color: var(--blue); font-size: 12px; font-weight: 700; }
.diagnosis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
}
.diagnosis-item {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px;
  background: #fbfdfc;
}
.diagnosis-item h3 { font-size: 14px; margin: 0 0 8px; }
.diagnosis-item p { margin: 6px 0; }
.diagnosis-item .status { min-width: 0; text-align: left; color: var(--muted); }
.band {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 16px;
  margin: 12px 0;
}
.split { display: grid; grid-template-columns: minmax(420px, 1fr) minmax(420px, 1fr); gap: 12px; }
.finding-row { display: flex; flex-wrap: wrap; gap: 8px; }
.badge {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 10px;
  background: #f8fbfa;
  font-size: 13px;
}
.critical { color: var(--bad); border-color: var(--bad); }
.warning { color: var(--warn); border-color: var(--warn); }
.info { color: var(--good); border-color: var(--good); }
.chart { width: 100%; height: 260px; display: block; border: 1px solid var(--line); background: #fbfdfc; }
.legend { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 10px; color: var(--muted); font-size: 13px; }
.swatch { display: inline-block; width: 16px; height: 3px; vertical-align: middle; margin-right: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
th, td { border-bottom: 1px solid var(--line); padding: 8px 6px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { color: var(--muted); font-size: 12px; font-weight: 700; }
.bar { height: 8px; background: #e3ded3; border-radius: 999px; overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--blue); }
.world-dashboard {
  background: var(--panel);
  border: 2px solid var(--ink);
  border-radius: 8px;
  padding: 18px;
  margin: 16px 0;
}
.world-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.world-day {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px 12px;
  min-width: 120px;
  text-align: right;
  color: var(--blue);
  font-weight: 700;
}
.world-layout {
  display: grid;
  grid-template-columns: minmax(420px, 1.25fr) minmax(280px, 0.75fr);
  gap: 16px;
  align-items: start;
}
.settlement-map {
  width: 100%;
  min-height: 420px;
  border: 1px solid var(--line);
  background: #fbfdfc;
  border-radius: 6px;
  display: block;
}
.route-line { stroke: #91a29e; stroke-width: 5; stroke-linecap: round; opacity: 0.72; }
.route-line.blocked { stroke: var(--bad); stroke-dasharray: 10 8; opacity: 0.88; }
.location-node { fill: #ffffff; stroke: var(--blue); stroke-width: 3; }
.location-node.low { stroke: var(--warn); }
.location-node.blocked { stroke: var(--bad); }
.location-label { font-size: 13px; font-weight: 700; fill: var(--ink); }
.location-meta { font-size: 11px; fill: var(--muted); }
.agent-dot { fill: var(--good); stroke: #ffffff; stroke-width: 2; }
.agent-dot.low { fill: var(--warn); }
.world-side {
  display: grid;
  gap: 12px;
}
.world-pulse {
  border-left: 4px solid var(--blue);
  padding-left: 12px;
}
.world-pulse ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--muted);
}
.world-pulse li { margin: 5px 0; }
.next-moves {
  border-left: 4px solid var(--good);
  padding-left: 12px;
}
.next-move {
  margin: 8px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.next-move:last-child { border-bottom: 0; }
.agent-life-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.agent-life {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px;
  background: #fbfdfc;
  min-height: 210px;
}
.agent-life h3 { margin-top: 0; }
.agent-life .role { color: var(--muted); font-size: 12px; }
.agent-life .plan { color: var(--blue); font-weight: 700; }
.agent-dossier-grid {
  display: grid;
  gap: 10px;
  margin: 16px 0;
}
.agent-dossier {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fbfdfc;
  padding: 10px 12px;
}
.agent-dossier summary {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.dossier-meta {
  color: var(--muted);
  font-size: 12px;
}
.timeline {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
.timeline-item {
  border-left: 3px solid var(--blue);
  padding-left: 10px;
}
.pressure-tags {
  color: var(--muted);
  font-size: 12px;
}
.mini-bars {
  display: grid;
  grid-template-columns: 48px 1fr 42px;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin: 6px 0;
}
.relationship-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.relationship-list {
  border-top: 1px solid var(--line);
  padding-top: 8px;
}
.relationship-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
}
.relationship-item:last-child { border-bottom: 0; }
@media (max-width: 900px) {
  .topbar { display: block; }
  .status { text-align: left; margin-top: 10px; }
  .metric-strip { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
  .world-head { display: block; }
  .world-day { text-align: left; margin-top: 10px; }
  .world-layout { grid-template-columns: 1fr; }
  .split { grid-template-columns: 1fr; }
}
</style>"""


def _metrics_chart(metrics: list[dict[str, Any]]) -> str:
    width = 1100
    height = 240
    padding = 24
    if not metrics:
        return "<p>No metrics recorded.</p>"
    need = [float(item["average_need"]) for item in metrics]
    trust = [float(item["average_trust"]) for item in metrics]
    reputation = [float(item["average_reputation"]) for item in metrics]
    cohesion = [float(item["institutional_cohesion"]) for item in metrics]
    food = [float(item["food"]) for item in metrics]
    max_food = max(max(food), 1.0)
    scaled_food = [value / max_food for value in food]
    return f"""
<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Metrics over time">
  <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" stroke="#c9c1b4" />
  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" stroke="#c9c1b4" />
  <polyline fill="none" stroke="#23785f" stroke-width="3" points="{_polyline(need, width, height, padding)}" />
  <polyline fill="none" stroke="#2f5d86" stroke-width="3" points="{_polyline(trust, width, height, padding)}" />
  <polyline fill="none" stroke="#6e5792" stroke-width="3" points="{_polyline(reputation, width, height, padding)}" />
  <polyline fill="none" stroke="#a33232" stroke-width="3" points="{_polyline(cohesion, width, height, padding)}" />
  <polyline fill="none" stroke="#a15c12" stroke-width="3" points="{_polyline(scaled_food, width, height, padding)}" />
</svg>
<div class="legend">
  <span><i class="swatch" style="background:#23785f"></i>average need</span>
  <span><i class="swatch" style="background:#2f5d86"></i>average trust</span>
  <span><i class="swatch" style="background:#6e5792"></i>average reputation</span>
  <span><i class="swatch" style="background:#a33232"></i>institutional cohesion</span>
  <span><i class="swatch" style="background:#a15c12"></i>food scaled to run max</span>
</div>"""


def _polyline(values: list[float], width: int, height: int, padding: int) -> str:
    if len(values) == 1:
        x_values = [width / 2]
    else:
        step = (width - padding * 2) / (len(values) - 1)
        x_values = [padding + step * index for index in range(len(values))]
    points = []
    for x, value in zip(x_values, values):
        y = height - padding - max(0.0, min(1.0, value)) * (height - padding * 2)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _agents_table(agents: list[dict[str, Any]]) -> str:
    rows = []
    for agent in agents:
        plan = agent.get("active_plan") or {}
        plan_text = plan.get("action", "none")
        rows.append(
            "<tr>"
            f"<td>{escape(agent['name'])}</td>"
            f"<td>{escape(agent['role'])}</td>"
            f"<td>{agent['average_need']}</td>"
            f"<td>{agent['average_trust']}</td>"
            f"<td>{agent.get('reputation', 0)}</td>"
            f"<td>{escape(agent.get('location_id', ''))}</td>"
            f"<td>{escape(', '.join(agent.get('organization_ids', [])))}</td>"
            f"<td>{escape(str(plan_text))}</td>"
            f"<td>{escape(_latest_reflection(agent))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Name</th><th>Role</th><th>Need</th><th>Trust</th><th>Rep</th><th>Location</th><th>Orgs</th><th>Plan</th><th>Latest Reflection</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _organizations_table(organizations: list[dict[str, Any]]) -> str:
    if not organizations:
        return "<p>No organizations recorded.</p>"
    rows = []
    for organization in organizations:
        rows.append(
            "<tr>"
            f"<td>{escape(organization['name'])}</td>"
            f"<td>{escape(organization['kind'])}</td>"
            f"<td>{escape(organization.get('home_location_id', 'commons'))}</td>"
            f"<td>{organization['cohesion']}</td>"
            f"<td>{organization['reputation']}</td>"
            f"<td>{escape(_resources_text(organization.get('inventory_targets', {})))}</td>"
            f"<td>{escape(', '.join(organization['members']))}</td>"
            f"<td>{escape(', '.join(organization['norms']))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Name</th><th>Kind</th><th>Home</th><th>Cohesion</th><th>Rep</th><th>Targets</th><th>Members</th><th>Norms</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _locations_table(locations: list[dict[str, Any]]) -> str:
    if not locations:
        return "<p>No locations recorded.</p>"
    rows = []
    for location in locations:
        condition_pct = max(0, min(100, int(location["condition"] * 100)))
        rows.append(
            "<tr>"
            f"<td>{escape(location['name'])}</td>"
            f"<td>{escape(location['kind'])}</td>"
            f"<td><div class=\"bar\"><span style=\"width:{condition_pct}%\"></span></div>{location['condition']}</td>"
            f"<td>{location['capacity']}</td>"
            f"<td>{escape(_resources_text(location.get('resources', {})))}</td>"
            f"<td>{escape(_resources_text(location.get('production', {})))}</td>"
            f"<td>{location.get('maintenance_need', 1.0)}</td>"
            f"<td>{escape(', '.join(location['connected_location_ids']))}</td>"
            f"<td>{escape(', '.join(location.get('blocked_connected_location_ids', [])))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Name</th><th>Kind</th><th>Condition</th><th>Cap</th><th>Resources</th><th>Production</th><th>Maint</th><th>Links</th><th>Blocked</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _story_cards(
    social_chronicle: dict[str, Any],
    cognition_trace: list[dict[str, Any]],
    generated_chains: list[dict[str, Any]],
    counterfactual_evaluation: dict[str, Any] | None,
    reason_richness: list[dict[str, Any]],
    baseline_comparison: dict[str, Any] | None,
) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    if baseline_comparison:
        cards.append(
            {
                "title": "Outcome against rule baseline",
                "summary": str(baseline_comparison.get("summary", "")),
                "evidence": _baseline_story_evidence(baseline_comparison.get("deltas", {})),
            }
        )

    if generated_chains:
        strongest = generated_chains[-1]
        cards.append(
            {
                "title": "Generated loop carried memory forward",
                "summary": (
                    f"{len(generated_chains)} generated chain(s) linked dialogue "
                    "to generated reflection and later planning evidence."
                ),
                "evidence": _generated_chain_story_evidence(strongest),
            }
        )

    divergent = sum(1 for item in cognition_trace if item.get("diverged_from_baseline"))
    blocked = sum(
        1
        for item in cognition_trace
        if item.get("status") in {"baseline_after_policy", "baseline_after_counterfactual"}
    )
    if cognition_trace:
        cards.append(
            {
                "title": "Generated cognition changed behavior",
                "summary": (
                    f"{divergent}/{len(cognition_trace)} generated cognition calls "
                    f"changed the executed plan; {blocked} proposals were blocked by policy."
                ),
                "evidence": _cognition_story_evidence(cognition_trace),
            }
        )

    if counterfactual_evaluation and counterfactual_evaluation.get("total"):
        cards.append(
            {
                "title": "Counterfactual gate filtered risk",
                "summary": str(counterfactual_evaluation.get("summary", "")),
                "evidence": _counterfactual_story_evidence(counterfactual_evaluation),
            }
        )

    rich = [
        item
        for item in reason_richness
        if str(item.get("signal", "")).startswith("reason_richness_richer")
    ]
    if rich:
        cards.append(
            {
                "title": "Reasons carried social evidence",
                "summary": (
                    f"{len(rich)} generated reasons used richer identity, memory, "
                    "relationship, or scar evidence than the rule baseline."
                ),
                "evidence": _reason_story_evidence(rich),
            }
        )

    for entry in reversed(social_chronicle.get("entries", [])):
        if entry.get("title") == "Routine adaptation":
            continue
        cards.append(
            {
                "title": str(entry.get("title", "Social change")),
                "summary": str(entry.get("summary", "")),
                "evidence": "; ".join(str(item) for item in (entry.get("evidence") or [])[:3]),
            }
        )
        break

    return cards[:4]


def _run_batch_summary(record: dict[str, Any]) -> dict[str, Any]:
    trace = record.get("cognition_trace") or []
    counterfactual = record.get("counterfactual_evaluation") or {}
    reason_richness = record.get("reason_richness") or []
    baseline = record.get("baseline_comparison") or {}
    final = record.get("final_metrics") or {}
    calls = len(trace)
    accepted = sum(1 for item in trace if item.get("status") == "primary")
    policy_fallbacks = sum(
        1
        for item in trace
        if item.get("status") in {"baseline_after_policy", "baseline_after_counterfactual"}
    )
    failures = sum(1 for item in trace if item.get("status") == "fallback_after_error")
    diverged = sum(1 for item in trace if item.get("diverged_from_baseline"))
    richer = sum(
        1
        for item in reason_richness
        if str(item.get("signal", "")).startswith("reason_richness_richer")
    )
    return {
        "seed": record.get("seed"),
        "days": record.get("days"),
        "final_metrics": final,
        "baseline_deltas": baseline.get("deltas", {}),
        "baseline_summary": baseline.get("summary", ""),
        "cognition_calls": calls,
        "accepted": accepted,
        "policy_fallbacks": policy_fallbacks,
        "failures": failures,
        "behavior_diverged": diverged,
        "behavior_divergence_rate": round(diverged / calls, 3) if calls else 0.0,
        "counterfactual_total": int(counterfactual.get("total", 0) or 0),
        "counterfactual_accepted": int(counterfactual.get("accepted", 0) or 0),
        "counterfactual_rejected": int(counterfactual.get("rejected", 0) or 0),
        "richer_reason_count": richer,
        "story_titles": [
            str(card.get("title", ""))
            for card in record.get("story_cards", [])
            if card.get("title")
        ],
    }


def _run_batch_aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    total_calls = sum(int(run.get("cognition_calls", 0)) for run in runs)
    total_diverged = sum(int(run.get("behavior_diverged", 0)) for run in runs)
    total_counterfactual = sum(int(run.get("counterfactual_total", 0)) for run in runs)
    total_counterfactual_accepted = sum(
        int(run.get("counterfactual_accepted", 0))
        for run in runs
    )
    average_deltas = {
        key: _average_delta(runs, key)
        for key in COMPARISON_METRICS
        if any(key in (run.get("baseline_deltas") or {}) for run in runs)
    }
    return {
        "total_cognition_calls": total_calls,
        "behavior_divergence_rate": round(total_diverged / total_calls, 3) if total_calls else 0.0,
        "counterfactual_acceptance_rate": (
            round(total_counterfactual_accepted / total_counterfactual, 3)
            if total_counterfactual
            else 0.0
        ),
        "counterfactual_rejected": sum(int(run.get("counterfactual_rejected", 0)) for run in runs),
        "richer_reason_count": sum(int(run.get("richer_reason_count", 0)) for run in runs),
        "runs_with_need_gain": _runs_with_positive_delta(runs, "average_need"),
        "runs_with_trust_gain": _runs_with_positive_delta(runs, "average_trust"),
        "runs_with_crisis_reduction": _runs_with_negative_delta(runs, "crisis_events"),
        "average_deltas": average_deltas,
    }


def _run_batch_story_cards(aggregate: dict[str, Any]) -> list[dict[str, str]]:
    run_count = max(
        aggregate.get("runs_with_need_gain", 0),
        aggregate.get("runs_with_trust_gain", 0),
        aggregate.get("runs_with_crisis_reduction", 0),
    )
    return [
        {
            "title": "Batch outcome signal",
            "summary": (
                f"{aggregate.get('runs_with_need_gain', 0)} runs improved need, "
                f"{aggregate.get('runs_with_trust_gain', 0)} improved trust, and "
                f"{aggregate.get('runs_with_crisis_reduction', 0)} reduced crisis events."
            ),
            "evidence": (
                f"average need {_signed_number(aggregate.get('average_deltas', {}).get('average_need', 0))}; "
                f"trust {_signed_number(aggregate.get('average_deltas', {}).get('average_trust', 0))}; "
                f"crisis {_signed_number(aggregate.get('average_deltas', {}).get('crisis_events', 0))}"
            ),
        },
        {
            "title": "Generated cognition stayed active",
            "summary": (
                f"{aggregate.get('total_cognition_calls', 0)} calls with "
                f"{_percent(aggregate.get('behavior_divergence_rate', 0))} executed-plan divergence."
            ),
            "evidence": f"{aggregate.get('richer_reason_count', 0)} generated reasons scored richer.",
        },
        {
            "title": "Counterfactual gate remained useful",
            "summary": (
                f"Gate acceptance was {_percent(aggregate.get('counterfactual_acceptance_rate', 0))}; "
                f"{aggregate.get('counterfactual_rejected', 0)} proposals were rejected."
            ),
            "evidence": f"positive run categories observed: {run_count}",
        },
    ]


def _run_batch_table(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return "<p>No run records loaded.</p>"
    rows = []
    for run in runs:
        deltas = run.get("baseline_deltas", {})
        final = run.get("final_metrics", {})
        rows.append(
            "<tr>"
            f"<td>{escape(str(run.get('seed', '')))}</td>"
            f"<td>{escape(str(run.get('days', '')))}</td>"
            f"<td>{escape(str(run.get('cognition_calls', 0)))}</td>"
            f"<td>{escape(str(run.get('accepted', 0)))}</td>"
            f"<td>{escape(str(run.get('policy_fallbacks', 0)))}</td>"
            f"<td>{escape(_percent(run.get('behavior_divergence_rate', 0)))}</td>"
            f"<td>{escape(str(run.get('counterfactual_accepted', 0)))}/"
            f"{escape(str(run.get('counterfactual_total', 0)))}</td>"
            f"<td>{escape(str(run.get('richer_reason_count', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('average_need', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('average_trust', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('crisis_events', 0)))}</td>"
            f"<td>{escape(str(final.get('average_need', '')))}</td>"
            f"<td>{escape('; '.join(run.get('story_titles') or []))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Seed</th><th>Days</th><th>Calls</th><th>Accepted</th><th>Blocked</th><th>Diverged</th><th>Gate</th><th>Richer Reasons</th><th>Need Delta</th><th>Trust Delta</th><th>Crisis Delta</th><th>Final Need</th><th>Story Cards</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _average_delta(runs: list[dict[str, Any]], key: str) -> float:
    values = [
        float((run.get("baseline_deltas") or {}).get(key))
        for run in runs
        if key in (run.get("baseline_deltas") or {})
    ]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _runs_with_positive_delta(runs: list[dict[str, Any]], key: str) -> int:
    return sum(
        1
        for run in runs
        if float((run.get("baseline_deltas") or {}).get(key, 0.0)) > 0
    )


def _runs_with_negative_delta(runs: list[dict[str, Any]], key: str) -> int:
    return sum(
        1
        for run in runs
        if float((run.get("baseline_deltas") or {}).get(key, 0.0)) < 0
    )


def _run_batch_status(aggregate: dict[str, Any]) -> str:
    deltas = aggregate.get("average_deltas", {})
    if deltas.get("average_need", 0) > 0 and deltas.get("average_trust", 0) > 0:
        return "Positive"
    if deltas.get("average_need", 0) < 0 and deltas.get("crisis_events", 0) > 0:
        return "Risk"
    return "Mixed"


def _story_cards_section(cards: list[dict[str, str]]) -> str:
    if not cards:
        return ""
    items = []
    for card in cards:
        items.append(
            "<article class=\"story-card\">"
            f"<h3>{escape(card.get('title', 'Story'))}</h3>"
            f"<p>{escape(card.get('summary', ''))}</p>"
            f"<p class=\"evidence\">{escape(card.get('evidence', ''))}</p>"
            "</article>"
        )
    return (
        "<section class=\"story-grid\" aria-label=\"Social story cards\">"
        + "".join(items)
        + "</section>"
    )


def _world_dashboard_section(record: dict[str, Any]) -> str:
    agents = record.get("agents", [])
    locations = record.get("locations", [])
    if not agents and not locations:
        return ""
    return (
        "<section class=\"world-dashboard\">"
        "<div class=\"world-head\">"
        "<div>"
        "<h2>World Dashboard</h2>"
        f"<p>{escape(_world_pulse_text(record))}</p>"
        "</div>"
        f"<div class=\"world-day\">Day {escape(str(record.get('days', '')))}</div>"
        "</div>"
        "<div class=\"world-layout\">"
        "<div>"
        "<h3>Settlement Map</h3>"
        f"{_settlement_map_svg(record)}"
        "</div>"
        "<div class=\"world-side\">"
        f"{_world_pulse_panel(record)}"
        f"{_observer_next_moves_panel(record.get('observer_recommendations', []))}"
        "</div>"
        "</div>"
        f"{_agent_life_cards(agents, record.get('relationship_links', []))}"
        f"{_relationship_dashboard(record)}"
        "</section>"
    )


def _world_pulse_text(record: dict[str, Any]) -> str:
    final = record.get("final_metrics") or {}
    scars = record.get("historical_scars") or {}
    relationship_count = len(scars.get("relationship_crises") or [])
    blocked_count = len(scars.get("blocked_routes") or [])
    need = final.get("average_need", "n/a")
    trust = final.get("average_trust", "n/a")
    cohesion = final.get("institutional_cohesion", "n/a")
    return (
        f"Need {need}, trust {trust}, cohesion {cohesion}; "
        f"{relationship_count} active relationship scars and {blocked_count} blocked routes define the current world state."
    )


def _world_pulse_panel(record: dict[str, Any]) -> str:
    chronicle = record.get("social_chronicle") or {}
    entries = list(chronicle.get("entries") or [])[-3:]
    lines = []
    if entries:
        for entry in entries:
            summary = str(entry.get("summary", ""))
            day_prefix = f"Day {entry.get('day', '')}:"
            lines.append(summary if summary.startswith(day_prefix) else f"{day_prefix} {summary}")
    else:
        for event in list(record.get("events") or [])[-3:]:
            lines.append(
                f"Day {event.get('day', '')}: {event.get('description', '')}"
            )
    if not lines:
        lines.append("No notable world story has been recorded yet.")
    items = "".join(f"<li>{escape(_short_text(line, 190))}</li>" for line in lines)
    return (
        "<div class=\"world-pulse\">"
        "<h3>Social Story</h3>"
        f"<p>{escape(str(chronicle.get('summary', 'Current social history is still forming.')))}</p>"
        f"<ul>{items}</ul>"
        "</div>"
    )


def _observer_next_moves_panel(recommendations: list[dict[str, Any]]) -> str:
    if not recommendations:
        return (
            "<div class=\"next-moves\">"
            "<h3>Observer Next Moves</h3>"
            "<p>No concrete observer recommendation is active.</p>"
            "</div>"
        )
    rows = []
    for item in recommendations[:4]:
        intervention = item.get("intervention") or {}
        rows.append(
            "<div class=\"next-move\">"
            f"<strong>{escape(str(item.get('title', 'Recommendation')))}</strong>"
            f"<p>{escape(str(item.get('expected_effect', '')))}</p>"
            f"<p>{escape(str(intervention.get('kind', '')))} on day {escape(str(intervention.get('day', '')))}</p>"
            "</div>"
        )
    return (
        "<div class=\"next-moves\">"
        "<h3>Observer Next Moves</h3>"
        + "".join(rows)
        + "</div>"
    )


def _settlement_map_svg(record: dict[str, Any]) -> str:
    locations = record.get("locations", [])
    agents = record.get("agents", [])
    if not locations:
        return "<p>No settlement map is available.</p>"
    width = 760
    height = 420
    positions = _location_positions(locations, width, height)
    blocked_routes = {
        str(item.get("route", ""))
        for item in (record.get("historical_scars") or {}).get("blocked_routes", [])
    }
    location_by_id = {str(location.get("id")): location for location in locations}
    agents_by_location: dict[str, list[dict[str, Any]]] = {}
    for agent in agents:
        agents_by_location.setdefault(str(agent.get("location_id", "")), []).append(agent)

    routes = []
    seen_routes: set[str] = set()
    for location in locations:
        source_id = str(location.get("id", ""))
        for target_id in location.get("connected_location_ids", []):
            target_id = str(target_id)
            key = _route_key(source_id, target_id)
            if key in seen_routes or source_id not in positions or target_id not in positions:
                continue
            seen_routes.add(key)
            x1, y1 = positions[source_id]
            x2, y2 = positions[target_id]
            route_class = "route-line blocked" if key in blocked_routes else "route-line"
            title = f"{key} blocked" if key in blocked_routes else key
            routes.append(
                f"<line class=\"{route_class}\" x1=\"{x1:.1f}\" y1=\"{y1:.1f}\" "
                f"x2=\"{x2:.1f}\" y2=\"{y2:.1f}\"><title>{escape(title)}</title></line>"
            )

    nodes = []
    for location_id, (x, y) in positions.items():
        location = location_by_id.get(location_id, {})
        condition = float(location.get("condition", 0.0) or 0.0)
        blocked_neighbors = location.get("blocked_connected_location_ids", [])
        node_class = "location-node"
        if blocked_neighbors:
            node_class += " blocked"
        elif condition < 0.55:
            node_class += " low"
        resources = location.get("resources") or {}
        resident_agents = agents_by_location.get(location_id, [])
        names = ", ".join(str(agent.get("name", "")) for agent in resident_agents)
        radius = 22 + min(9, len(resident_agents) * 2)
        nodes.append(
            "<g>"
            f"<circle class=\"{node_class}\" cx=\"{x:.1f}\" cy=\"{y:.1f}\" r=\"{radius}\">"
            f"<title>{escape(str(location.get('name', location_id)))} | {escape(_resources_text(resources))} | {escape(names)}</title>"
            "</circle>"
            f"<text class=\"location-label\" x=\"{x:.1f}\" y=\"{y + radius + 17:.1f}\" text-anchor=\"middle\">"
            f"{escape(str(location.get('name', location_id)))}</text>"
            f"<text class=\"location-meta\" x=\"{x:.1f}\" y=\"{y + radius + 32:.1f}\" text-anchor=\"middle\">"
            f"cond {condition:.2f} | {len(resident_agents)} agents</text>"
            f"{_agent_dots_svg(resident_agents, x, y, radius)}"
            "</g>"
        )

    return (
        f"<svg class=\"settlement-map\" viewBox=\"0 0 {width} {height}\" role=\"img\" "
        "aria-label=\"Settlement map with locations, routes, blocked routes, and agent positions\">"
        f"{''.join(routes)}{''.join(nodes)}"
        "<g transform=\"translate(18 18)\">"
        "<line class=\"route-line\" x1=\"0\" y1=\"0\" x2=\"34\" y2=\"0\" />"
        "<text class=\"location-meta\" x=\"44\" y=\"4\">open route</text>"
        "<line class=\"route-line blocked\" x1=\"0\" y1=\"22\" x2=\"34\" y2=\"22\" />"
        "<text class=\"location-meta\" x=\"44\" y=\"26\">blocked route</text>"
        "</g>"
        "</svg>"
    )


def _location_positions(
    locations: list[dict[str, Any]],
    width: int,
    height: int,
) -> dict[str, tuple[float, float]]:
    import math

    center = (width / 2, height / 2)
    location_ids = [str(location.get("id", "")) for location in locations]
    positions: dict[str, tuple[float, float]] = {}
    outer_ids = [location_id for location_id in location_ids if location_id != "commons"]
    if "commons" in location_ids:
        positions["commons"] = center
    else:
        outer_ids = location_ids
    radius_x = width * 0.36
    radius_y = height * 0.32
    for index, location_id in enumerate(outer_ids):
        angle = (math.tau * index / max(1, len(outer_ids))) - math.pi / 2
        positions[location_id] = (
            center[0] + math.cos(angle) * radius_x,
            center[1] + math.sin(angle) * radius_y,
        )
    return positions


def _agent_dots_svg(
    agents: list[dict[str, Any]],
    x: float,
    y: float,
    radius: float,
) -> str:
    if not agents:
        return ""
    import math

    dots = []
    dot_radius = 5.5
    orbit = radius + 12
    for index, agent in enumerate(agents[:10]):
        angle = math.tau * index / max(1, min(len(agents), 10))
        dx = x + math.cos(angle) * orbit
        dy = y + math.sin(angle) * orbit
        low = float(agent.get("average_need", 1.0) or 1.0) < 0.36
        dot_class = "agent-dot low" if low else "agent-dot"
        dots.append(
            f"<circle class=\"{dot_class}\" cx=\"{dx:.1f}\" cy=\"{dy:.1f}\" r=\"{dot_radius}\">"
            f"<title>{escape(str(agent.get('name', 'agent')))} | {escape(str(agent.get('role', '')))}</title>"
            "</circle>"
        )
    return "".join(dots)


def _agent_life_cards(
    agents: list[dict[str, Any]],
    relationship_links: list[dict[str, Any]],
) -> str:
    if not agents:
        return ""
    ranked = sorted(
        agents,
        key=lambda agent: (
            float(agent.get("average_need", 1.0) or 1.0),
            str(agent.get("name", "")),
        ),
    )
    cards = []
    for agent in ranked[:12]:
        plan = agent.get("active_plan") or {}
        plan_text = (
            f"{plan.get('action', 'none')}: {plan.get('reason', '')}"
            if plan
            else "none"
        )
        cards.append(
            "<article class=\"agent-life\">"
            f"<h3>{escape(str(agent.get('name', 'Agent')))}</h3>"
            f"<div class=\"role\">{escape(str(agent.get('role', '')))} @ {escape(str(agent.get('location_id', '')))}</div>"
            f"{_mini_bar('need', agent.get('average_need', 0))}"
            f"{_mini_bar('trust', agent.get('average_trust', 0))}"
            f"<p class=\"plan\">{escape(_short_text(plan_text, 130))}</p>"
            f"<p><strong>Daily Life:</strong> {escape(_short_text(_latest_life_episode(agent), 170))}</p>"
            f"<p>{escape(_agent_social_state(agent, relationship_links))}</p>"
            f"<p>{escape(_short_text(_latest_reflection(agent), 150))}</p>"
            "</article>"
        )
    return (
        "<div class=\"agent-life-grid\" aria-label=\"Agent life cards\">"
        + "".join(cards)
        + "</div>"
    )


def _mini_bar(label: str, value: Any) -> str:
    numeric = max(0.0, min(1.0, float(value or 0.0)))
    width = int(numeric * 100)
    return (
        "<div class=\"mini-bars\">"
        f"<span>{escape(label)}</span>"
        f"<div class=\"bar\"><span style=\"width:{width}%\"></span></div>"
        f"<span>{numeric:.3f}</span>"
        "</div>"
    )


def _agent_social_state(
    agent: dict[str, Any],
    relationship_links: list[dict[str, Any]],
) -> str:
    agent_id = str(agent.get("id", ""))
    links = [
        link
        for link in relationship_links
        if agent_id in {str(value) for value in link.get("agent_ids", [])}
    ]
    if not links:
        return "No relationship evidence yet."
    crisis_count = sum(1 for link in links if link.get("crisis"))
    weakest = min(links, key=lambda link: float(link.get("average_trust", 1.0)))
    other_names = [
        str(name)
        for name, other_id in zip(weakest.get("agents", []), weakest.get("agent_ids", []))
        if str(other_id) != agent_id
    ]
    other = other_names[0] if other_names else "unknown"
    return (
        f"{crisis_count} active crises; weakest tie {other} "
        f"at {float(weakest.get('average_trust', 0.0)):.3f}."
    )


def _relationship_dashboard(record: dict[str, Any]) -> str:
    scars = record.get("historical_scars") or {}
    crisis_items = list(scars.get("relationship_crises") or [])[:8]
    weak_links = sorted(
        record.get("relationship_links", []),
        key=lambda item: float(item.get("average_trust", 1.0)),
    )[:8]
    if not crisis_items and not weak_links:
        return ""
    return (
        "<h3>Relationship Web</h3>"
        "<div class=\"relationship-panel\">"
        f"{_relationship_list('Active Relationship Scars', crisis_items, crisis=True)}"
        f"{_relationship_list('Weakest Current Ties', weak_links, crisis=False)}"
        "</div>"
    )


def _relationship_list(
    title: str,
    items: list[dict[str, Any]],
    crisis: bool,
) -> str:
    if not items:
        return ""
    rows = []
    for item in items:
        agents = " / ".join(str(value) for value in item.get("agents", []))
        trust = item.get("average_trust", 0)
        detail = (
            f"since day {item.get('started_day', '')}"
            if crisis
            else ("crisis" if item.get("crisis") else "open")
        )
        rows.append(
            "<div class=\"relationship-item\">"
            f"<span>{escape(agents)}</span>"
            f"<strong>{escape(str(trust))}</strong>"
            f"<span>{escape(str(detail))}</span>"
            "</div>"
        )
    return (
        "<div class=\"relationship-list\">"
        f"<h3>{escape(title)}</h3>"
        + "".join(rows)
        + "</div>"
    )


def _agent_dossiers_section(record: dict[str, Any]) -> str:
    agents = record.get("agents") or []
    if not agents:
        return ""
    relationship_links = record.get("relationship_links") or []
    ranked = sorted(
        agents,
        key=lambda agent: (
            float(agent.get("average_need", 1.0) or 1.0),
            str(agent.get("name", "")),
        ),
    )
    dossiers = [
        _agent_dossier(agent, relationship_links)
        for agent in ranked[:12]
    ]
    return (
        "<section class=\"band\">"
        "<h2>Agent Dossiers</h2>"
        "<p>Expandable individual timelines built from validated world state, daily life, memory, and relationship evidence.</p>"
        f"<div class=\"agent-dossier-grid\">{''.join(dossiers)}</div>"
        "</section>"
    )


def _agent_dossier(
    agent: dict[str, Any],
    relationship_links: list[dict[str, Any]],
) -> str:
    name = str(agent.get("name", "Agent"))
    role = str(agent.get("role", ""))
    location_id = str(agent.get("location_id", ""))
    need = agent.get("average_need", "")
    trust = agent.get("average_trust", "")
    return (
        "<details class=\"agent-dossier\">"
        "<summary>"
        f"<span><strong>{escape(name)}</strong> <span class=\"dossier-meta\">{escape(role)} @ {escape(location_id)}</span></span>"
        f"<span class=\"dossier-meta\">need {escape(str(need))} | trust {escape(str(trust))}</span>"
        "</summary>"
        f"{_life_timeline(agent)}"
        f"{_agent_memory_panel(agent)}"
        f"{_agent_relationship_panel(agent, relationship_links)}"
        "</details>"
    )


def _life_timeline(agent: dict[str, Any]) -> str:
    entries = list(agent.get("recent_life_journal") or [])[-5:]
    if not entries:
        return "<h3>Life Timeline</h3><p>No life journal entries yet.</p>"
    rows = []
    for entry in reversed(entries):
        pressures = ", ".join(str(item) for item in entry.get("pressures", [])[:4])
        rows.append(
            "<div class=\"timeline-item\">"
            f"<strong>Day {escape(str(entry.get('day', '')))} · {escape(str(entry.get('mood', 'steady')))}</strong>"
            f"<p>{escape(str(entry.get('summary', '')))}</p>"
            f"<div class=\"pressure-tags\">{escape(pressures)}</div>"
            "</div>"
        )
    return "<h3>Life Timeline</h3><div class=\"timeline\">" + "".join(rows) + "</div>"


def _agent_memory_panel(agent: dict[str, Any]) -> str:
    memories = list(agent.get("recent_memory_stream") or [])[-4:]
    if not memories:
        return "<h3>Recent Memory</h3><p>No memory stream entries yet.</p>"
    items = "".join(
        "<li>"
        f"day {escape(str(memory.get('day', '')))} · {escape(str(memory.get('kind', '')))}: "
        f"{escape(_short_text(memory.get('text', ''), 180))}"
        "</li>"
        for memory in reversed(memories)
    )
    return f"<h3>Recent Memory</h3><ul>{items}</ul>"


def _agent_relationship_panel(
    agent: dict[str, Any],
    relationship_links: list[dict[str, Any]],
) -> str:
    agent_id = str(agent.get("id", ""))
    links = [
        link
        for link in relationship_links
        if agent_id in {str(value) for value in link.get("agent_ids", [])}
    ]
    if not links:
        return "<h3>Relationship Pressure</h3><p>No relationship evidence yet.</p>"
    rows = []
    for link in sorted(links, key=lambda item: float(item.get("average_trust", 1.0)))[:5]:
        other_names = [
            str(name)
            for name, other_id in zip(link.get("agents", []), link.get("agent_ids", []))
            if str(other_id) != agent_id
        ]
        state = "crisis" if link.get("crisis") else "open"
        rows.append(
            "<li>"
            f"{escape(other_names[0] if other_names else 'unknown')} · "
            f"trust {escape(str(link.get('average_trust', '')))} · {escape(state)}"
            "</li>"
        )
    return "<h3>Relationship Pressure</h3><ul>" + "".join(rows) + "</ul>"


def _run_diagnosis(record: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    chains = record.get("generated_chains") or []
    scars = record.get("historical_scars") or {}
    scar_diagnosis = record.get("scar_diagnosis") or []
    trace = record.get("cognition_trace") or []
    comparison = record.get("baseline_comparison") or {}
    findings = record.get("findings") or []

    if chains:
        strongest = chains[-1]
        items.append(
            {
                "area": "Generated loop",
                "status": "active",
                "evidence": _generated_chain_story_evidence(strongest),
                "next": "Use this chain as the observer-facing explanation of how dialogue became later planning pressure.",
            }
        )

    relationship_count = len(scars.get("relationship_crises") or [])
    if relationship_count:
        relationship_bottlenecks = [
            item
            for item in scar_diagnosis
            if item.get("kind") == "relationship_crisis"
        ]
        top = relationship_bottlenecks[0] if relationship_bottlenecks else {}
        social_count = _used_action_count(trace, "socialize")
        items.append(
            {
                "area": "Relationship pressure",
                "status": str(top.get("status") or "open"),
                "evidence": (
                    f"{relationship_count} active relationship crises remain; "
                    f"generated cognition executed {social_count} social plan(s). "
                    f"{top.get('summary', '')}"
                ),
                "next": str(
                    top.get("next_step")
                    or "Compare social repair against food and route duties before increasing provider call volume."
                ),
            }
        )

    blocked_count = len(scars.get("blocked_routes") or [])
    if blocked_count:
        route_bottlenecks = [
            item
            for item in scar_diagnosis
            if item.get("kind") == "blocked_route"
        ]
        top = route_bottlenecks[0] if route_bottlenecks else {}
        repair_count = _used_action_count(trace, "repair")
        haul_count = _used_action_count(trace, "haul")
        items.append(
            {
                "area": "Route pressure",
                "status": str(top.get("status") or "blocked"),
                "evidence": (
                    f"{blocked_count} blocked route(s) remain; generated cognition "
                    f"executed {repair_count} repair and {haul_count} haul plan(s). "
                    f"{top.get('summary', '')}"
                ),
                "next": str(
                    top.get("next_step")
                    or "Diagnose whether repair lacks materials, agent budget, or better target selection."
                ),
            }
        )

    deltas = comparison.get("deltas") or {}
    if deltas:
        items.append(
            {
                "area": "Rule baseline delta",
                "status": "partial",
                "evidence": _baseline_story_evidence(deltas),
                "next": "Treat improvement over baseline as evidence, but keep residual crises visible.",
            }
        )

    unresolved = [
        item
        for item in findings
        if str(item.get("severity", "")).lower() in {"critical", "warning"}
    ]
    if unresolved:
        finding = unresolved[0]
        items.append(
            {
                "area": "Health floor",
                "status": str(finding.get("severity", "warning")),
                "evidence": str(finding.get("description") or finding.get("code") or ""),
                "next": "Resolve this world-layer bottleneck before treating richer language as real social progress.",
            }
        )

    return items[:5]


def _run_diagnosis_section(items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        cards.append(
            "<article class=\"diagnosis-item\">"
            f"<h3>{escape(item.get('area', 'Diagnosis'))}</h3>"
            f"<p class=\"status\">{escape(item.get('status', 'observed'))}</p>"
            f"<p>{escape(item.get('evidence', ''))}</p>"
            f"<p class=\"evidence\">{escape(item.get('next', ''))}</p>"
            "</article>"
        )
    return (
        "<section class=\"band\">"
        "<h2>Run Diagnosis</h2>"
        "<p>Readable causal checkpoints for generated behavior and remaining world pressure.</p>"
        f"<div class=\"diagnosis-grid\">{''.join(cards)}</div>"
        "</section>"
    )


def _generated_chain_story_evidence(item: dict[str, Any]) -> str:
    shared = ", ".join(item.get("shared_terms") or []) or "no shared terms"
    return (
        f"day {item.get('dialogue_day')} -> {item.get('reflection_day')}: "
        f"{item.get('speaker_name', '')}/{item.get('partner_name', '')} to "
        f"{item.get('reflection_agent_name', '')}; "
        f"{item.get('signal', '')}; shared {shared}"
    )


def _used_action_count(trace: list[dict[str, Any]], action: str) -> int:
    count = 0
    for item in trace:
        if item.get("status") != "primary":
            continue
        used = item.get("used_plan") or {}
        if used.get("action") == action:
            count += 1
    return count


def _baseline_story_evidence(deltas: dict[str, Any]) -> str:
    if not deltas:
        return "No metric deltas recorded."
    keys = ["average_need", "average_trust", "shelter", "crisis_events"]
    return "; ".join(
        f"{key} {_signed_number(deltas[key])}"
        for key in keys
        if key in deltas
    )


def _cognition_story_evidence(trace: list[dict[str, Any]]) -> str:
    examples = []
    for item in trace:
        if not item.get("diverged_from_baseline"):
            continue
        proposed = item.get("proposed_plan") or {}
        used = item.get("used_plan") or {}
        baseline = item.get("baseline_plan") or {}
        examples.append(
            f"day {item.get('day')}: {item.get('agent_name')} "
            f"{baseline.get('action')} -> {used.get('action') or proposed.get('action')}"
        )
        if len(examples) >= 3:
            break
    return "; ".join(examples) or "No executed plan divergence."


def _counterfactual_story_evidence(evaluation: dict[str, Any]) -> str:
    accepted = evaluation.get("accepted", 0)
    rejected = evaluation.get("rejected", 0)
    total = evaluation.get("total", 0)
    return f"accepted {accepted}/{total}; rejected {rejected}/{total}"


def _reason_story_evidence(items: list[dict[str, Any]]) -> str:
    examples = []
    for item in items[:3]:
        groups = ", ".join(item.get("generated_groups") or [])
        examples.append(
            f"day {item.get('day')}: {item.get('agent_name')} used {groups}"
        )
    return "; ".join(examples)


def _social_chronicle_section(chronicle: dict[str, Any] | None) -> str:
    if not chronicle or not chronicle.get("entries"):
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Social Chronicle</h2>"
        f"<p>{escape(str(chronicle.get('summary', '')))}</p>"
        f"{_social_chronicle_table(chronicle.get('entries', []))}"
        f"{_evaluation_signal_table(chronicle.get('evaluation_signals', []))}"
        "</section>"
    )


def _social_chronicle_table(entries: list[dict[str, Any]]) -> str:
    rows = []
    for entry in entries:
        evidence = entry.get("evidence") or []
        rows.append(
            "<tr>"
            f"<td>{entry.get('day', '')}</td>"
            f"<td>{escape(str(entry.get('title', '')))}</td>"
            f"<td>{escape(str(entry.get('summary', '')))}</td>"
            f"<td>{escape('; '.join(str(item) for item in evidence[:4]))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Story</th><th>Summary</th><th>Evidence</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _evaluation_signal_table(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return ""
    rows = []
    for item in signals[:8]:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('severity', '')))}</td>"
            f"<td>{escape(str(item.get('code', '')))}</td>"
            f"<td>{escape(str(item.get('description', '')))}</td>"
            "</tr>"
        )
    return "<h3>Evaluation Signals</h3><table><thead><tr><th>Severity</th><th>Code</th><th>Description</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _observer_recommendations_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Observer Intervention Suggestions</h2>"
        "<p>Concrete observer actions derived from residual scar bottlenecks.</p>"
        f"{_observer_recommendations_table(items)}"
        "</section>"
    )


def _observer_recommendations_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[:12]:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('priority', '')))}</td>"
            f"<td>{escape(str(item.get('title', '')))}</td>"
            f"<td>{escape(str(item.get('rationale', '')))}</td>"
            f"<td>{escape(str(item.get('expected_effect', '')))}</td>"
            f"<td>{escape(_recommendation_intervention_text(item.get('intervention') or {}))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Priority</th><th>Recommendation</th><th>Rationale</th><th>Expected effect</th><th>Intervention</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _recommendation_intervention_text(intervention: dict[str, Any]) -> str:
    if not intervention:
        return ""
    params = intervention.get("params") or {}
    return (
        f"day {intervention.get('day')}: {intervention.get('kind')} | "
        f"{intervention.get('reason', '')} | {json.dumps(params, ensure_ascii=False, sort_keys=True)}"
    )


def _observer_intent_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Observer Intent Follow-through</h2>"
        "<p>Targeted observer broadcasts linked to agent memories and later plans.</p>"
        f"{_observer_intent_table(items)}"
        "</section>"
    )


def _observer_intent_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item.get('day', '')}</td>"
            f"<td>{escape(str(item.get('intent', '')))}</td>"
            f"<td>{escape(str(item.get('signal', '')))}</td>"
            f"<td>{item.get('memory_hits', 0)}/{item.get('expected_targets', 0)}</td>"
            f"<td>{item.get('plan_hits', 0)}</td>"
            f"<td>{escape(', '.join(item.get('target_agents') or []))}</td>"
            f"<td>{escape(_observer_intent_evidence_text(item))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Intent</th><th>Signal</th><th>Memory</th><th>Plans</th><th>Targets</th><th>Evidence</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _observer_intent_evidence_text(item: dict[str, Any]) -> str:
    evidence = item.get("plan_evidence") or []
    if not evidence:
        return "none"
    return " | ".join(str(value) for value in evidence[:3])


def _observer_memory_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Observer Memory</h2>"
        "<p>Named observer interventions that entered the event log and can become agent memory.</p>"
        f"{_observer_memory_table(items)}"
        "</section>"
    )


def _observer_memory_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item.get('day', '')}</td>"
            f"<td>{escape(str(item.get('actor_id', '')))}</td>"
            f"<td>{escape(str(item.get('kind', '')))}</td>"
            f"<td>{escape(str(item.get('description', '')))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Observer</th><th>Kind</th><th>Description</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _scar_diagnosis_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Residual Scar Diagnosis</h2>"
        "<p>Why active relationship crises and blocked routes have not cleared yet.</p>"
        f"{_scar_diagnosis_table(items)}"
        "</section>"
    )


def _scar_diagnosis_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[:30]:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('kind', '')))}</td>"
            f"<td>{escape(str(item.get('subject', '')))}</td>"
            f"<td>{escape(str(item.get('severity', '')))}</td>"
            f"<td>{escape(str(item.get('status', '')))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            f"<td>{escape(_scar_evidence_text(item))}</td>"
            f"<td>{escape(str(item.get('next_step', '')))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Kind</th><th>Subject</th><th>Severity</th><th>Status</th><th>Summary</th><th>Evidence</th><th>Next</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _scar_evidence_text(item: dict[str, Any]) -> str:
    evidence = item.get("evidence") or []
    if not evidence:
        return ""
    return " | ".join(str(value) for value in evidence[:4])


def _historical_scar_validation_section(validation: dict[str, Any] | None) -> str:
    if not validation:
        return ""
    findings = validation.get("findings", [])
    if not findings:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Historical Scar Validation</h2>"
        f"<p>{escape(str(validation.get('summary', '')))}</p>"
        f"{_historical_scar_validation_table(findings)}"
        "</section>"
    )


def _historical_scar_validation_table(findings: list[dict[str, Any]]) -> str:
    rows = []
    for finding in findings:
        rows.append(
            "<tr>"
            f"<td>{escape(str(finding.get('status', '')))}</td>"
            f"<td>{escape(str(finding.get('code', '')))}</td>"
            f"<td>{escape(str(finding.get('description', '')))}</td>"
            f"<td>{finding.get('value', 0)}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Status</th><th>Code</th><th>Description</th><th>Value</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _historical_scars(world: WorldState) -> dict[str, Any]:
    agents_by_id = {agent.id: agent for agent in world.agents}
    relationship_crises = []
    for pair_key, started_day in sorted(world.relationship_crises.items()):
        first_id, second_id = pair_key.split("|", 1)
        first = agents_by_id.get(first_id)
        second = agents_by_id.get(second_id)
        first_trust = first.relationships.get(second_id, 0.0) if first is not None else 0.0
        second_trust = second.relationships.get(first_id, 0.0) if second is not None else 0.0
        relationship_crises.append(
            {
                "pair": pair_key,
                "started_day": started_day,
                "agents": [
                    first.name if first is not None else first_id,
                    second.name if second is not None else second_id,
                ],
                "average_trust": round((first_trust + second_trust) / 2, 3),
            }
        )

    return {
        "relationship_crises": relationship_crises,
        "blocked_routes": [
            {"route": key, "repair_need": round(value, 3)}
            for key, value in sorted(world.blocked_routes.items())
        ],
        "organization_fractures": [
            {"organization_id": key, "day": value}
            for key, value in sorted(world.organization_fractures.items())
        ],
    }


def _observer_memory(world: WorldState) -> list[dict[str, Any]]:
    agent_ids = {agent.id for agent in world.agents}
    organization_ids = {organization.id for organization in world.organizations}
    observer_events = []
    for event in world.event_log:
        if event.actor_id in agent_ids or event.actor_id in organization_ids:
            continue
        if event.actor_id in {"society", "common_council"}:
            continue
        if event.kind not in {
            "intervention",
            "broadcast",
            "disaster",
            "edict",
            "arrival",
            "organization",
        }:
            continue
        observer_events.append(
            {
                "day": event.day,
                "actor_id": event.actor_id,
                "kind": event.kind,
                "description": event.description,
                "effects": dict(event.effects),
            }
        )
    return observer_events


def _historical_scars_section(scars: dict[str, Any]) -> str:
    if not scars:
        return ""
    relationship_crises = scars.get("relationship_crises") or []
    blocked_routes = scars.get("blocked_routes") or []
    organization_fractures = scars.get("organization_fractures") or []
    if not relationship_crises and not blocked_routes and not organization_fractures:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Historical Scars</h2>"
        "<p>Persistent social and spatial damage that will not vanish through passive drift.</p>"
        f"{_relationship_crisis_table(relationship_crises)}"
        f"{_blocked_route_table(blocked_routes)}"
        f"{_organization_fracture_table(organization_fractures)}"
        "</section>"
    )


def _relationship_crisis_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{escape(' / '.join(item.get('agents', [])))}</td>"
            f"<td>{item.get('started_day', '')}</td>"
            f"<td>{item.get('average_trust', 0)}</td>"
            "</tr>"
        )
    return "<h3>Relationship Crises</h3><table><thead><tr><th>Agents</th><th>Since Day</th><th>Trust</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _blocked_route_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('route', '')))}</td>"
            f"<td>{item.get('repair_need', 0)}</td>"
            "</tr>"
        )
    return "<h3>Blocked Routes</h3><table><thead><tr><th>Route</th><th>Repair Need</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _organization_fracture_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('organization_id', '')))}</td>"
            f"<td>{item.get('day', '')}</td>"
            "</tr>"
        )
    return "<h3>Organization Fractures</h3><table><thead><tr><th>Organization</th><th>Day</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _history_section(history: dict[str, Any] | None) -> str:
    if not history:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>History</h2>"
        f"<p>{escape(history['summary'])}</p>"
        f"{_history_table(history.get('snapshots', []))}"
        "</section>"
    )


def _history_table(snapshots: list[dict[str, Any]]) -> str:
    if not snapshots:
        return "<p>No history snapshots recorded.</p>"
    rows = []
    for snapshot in snapshots:
        metrics = snapshot["metrics"]
        event_counts = snapshot.get("event_counts", {})
        notable_events = sum(
            int(event_counts.get(kind, 0))
            for kind in (
                "disaster",
                "hunger_crisis",
                "institutional_crisis",
                "organization",
                "organization_fracture",
                "rationing",
                "relationship_crisis",
                "route_blocked",
            )
        )
        rows.append(
            "<tr>"
            f"<td>{snapshot['day']}</td>"
            f"<td>{metrics['average_need']}</td>"
            f"<td>{metrics['average_trust']}</td>"
            f"<td>{metrics['average_reputation']}</td>"
            f"<td>{metrics['institutional_cohesion']}</td>"
            f"<td>{notable_events}</td>"
            f"<td>{escape(snapshot['summary'])}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Need</th><th>Trust</th><th>Rep</th><th>Cohesion</th><th>Notable</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _llm_cache_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>LLM Cache</h2>"
        "<p>Raw prompt/response cache activity for generated providers in this run.</p>"
        f"{_llm_cache_table(items)}"
        "</section>"
    )


def _llm_cache_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('surface', '')))}</td>"
            f"<td>{escape(str(item.get('mode', '')))}</td>"
            f"<td>{escape(str(item.get('provider', '')))}</td>"
            f"<td>{escape(str(item.get('model', '')))}</td>"
            f"<td>{item.get('reads', 0)}</td>"
            f"<td>{item.get('hits', 0)}</td>"
            f"<td>{item.get('misses', 0)}</td>"
            f"<td>{item.get('writes', 0)}</td>"
            f"<td>{escape(str(item.get('root_dir', '')))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Surface</th><th>Mode</th><th>Provider</th><th>Model</th><th>Reads</th><th>Hits</th><th>Misses</th><th>Writes</th><th>Directory</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _counterfactual_evaluation_section(evaluation: dict[str, Any] | None) -> str:
    if not evaluation or not evaluation.get("total"):
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Counterfactual Evaluation</h2>"
        f"<p>{escape(str(evaluation.get('summary', '')))}</p>"
        f"{_counterfactual_overview_table(evaluation)}"
        f"{_counterfactual_bucket_table('By Agent', evaluation.get('by_agent') or [])}"
        f"{_counterfactual_bucket_table('By Action Pair', evaluation.get('by_action_pair') or [])}"
        "</section>"
    )


def _counterfactual_overview_table(evaluation: dict[str, Any]) -> str:
    rows = []
    for key, label in (
        ("total", "Total"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("acceptance_rate", "Acceptance Rate"),
        ("average_score_delta", "Avg Score Delta"),
        ("worst_score_delta", "Worst Delta"),
        ("best_score_delta", "Best Delta"),
    ):
        rows.append(
            "<tr>"
            f"<td>{escape(label)}</td>"
            f"<td>{escape(str(evaluation.get(key, 0)))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _counterfactual_bucket_table(title: str, buckets: list[dict[str, Any]]) -> str:
    if not buckets:
        return ""
    rows = []
    for item in buckets[:12]:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('label', '')))}</td>"
            f"<td>{item.get('total', 0)}</td>"
            f"<td>{item.get('accepted', 0)}</td>"
            f"<td>{item.get('rejected', 0)}</td>"
            f"<td>{escape(_signed_number(item.get('average_score_delta', 0)))}</td>"
            f"<td>{escape(_signed_number(item.get('worst_score_delta', 0)))}</td>"
            f"<td>{escape(_signed_number(item.get('best_score_delta', 0)))}</td>"
            "</tr>"
        )
    return (
        f"<h3>{escape(title)}</h3>"
        "<table><thead><tr><th>Label</th><th>Total</th><th>Accepted</th>"
        "<th>Rejected</th><th>Avg Delta</th><th>Worst</th><th>Best</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _events_table(events: list[dict[str, Any]]) -> str:
    rows = []
    for event in reversed(events):
        rows.append(
            "<tr>"
            f"<td>{event['day']}</td>"
            f"<td>{escape(event['kind'])}</td>"
            f"<td>{escape(event['actor_id'])}</td>"
            f"<td>{escape(event['description'])}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Kind</th><th>Actor</th><th>Description</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _cognition_trace_section(trace: list[dict[str, Any]]) -> str:
    if not trace:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Cognition Trace</h2>"
        f"<p>{escape(_cognition_trace_summary(trace))}</p>"
        f"{_cognition_trace_table(trace)}"
        "</section>"
    )


def _cognition_trace_table(trace: list[dict[str, Any]]) -> str:
    rows = []
    for item in trace[-30:]:
        proposed = item.get("proposed_plan") or {}
        baseline = item.get("baseline_plan") or {}
        used = item.get("used_plan") or {}
        counterfactual = item.get("counterfactual") or {}
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['agent_name'])}</td>"
            f"<td>{escape(str(item.get('prompt_version') or 'unknown'))}</td>"
            f"<td>{escape(item['status'])}</td>"
            f"<td>{escape(_plan_summary(proposed))}</td>"
            f"<td>{escape(_plan_summary(baseline))}</td>"
            f"<td>{escape(_plan_summary(used))}</td>"
            f"<td>{escape(str(item.get('diverged_from_baseline', False)))}</td>"
            f"<td>{escape(_counterfactual_summary(counterfactual))}</td>"
            f"<td>{escape(str(item.get('error') or ''))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Prompt</th><th>Status</th><th>Codex Plan</th><th>Rule Baseline</th><th>Used</th><th>Diverged</th><th>Counterfactual</th><th>Error</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _cognition_impacts_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Cognition Impact Evaluation</h2>"
        "<p>Accepted or blocked generated plan proposals linked to execution "
        "evidence and rule-baseline plan differences.</p>"
        f"{_cognition_impacts_table(items)}"
        "</section>"
    )


def _cognition_impacts_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['agent_name'])}</td>"
            f"<td>{escape(item.get('status') or '')}</td>"
            f"<td>{escape(item.get('signal') or '')}</td>"
            f"<td>{escape(str(item.get('baseline_action') or 'none'))}</td>"
            f"<td>{escape(str(item.get('proposed_action') or 'none'))}</td>"
            f"<td>{escape(str(item.get('used_action') or 'none'))}</td>"
            f"<td>{len(item.get('execution_evidence') or [])}</td>"
            f"<td>{len(item.get('baseline_plan_deltas') or [])}</td>"
            f"<td>{escape(_cognition_impact_evidence_text(item))}</td>"
            f"<td>{escape(item.get('summary') or '')}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Status</th><th>Signal</th><th>Rule</th><th>Proposed</th><th>Used</th><th>Execution</th><th>Plan deltas</th><th>Evidence sample</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _cognition_impact_evidence_text(item: dict[str, Any]) -> str:
    parts = []
    execution = item.get("execution_evidence") or []
    deltas = item.get("baseline_plan_deltas") or []
    if execution:
        parts.append(
            f"execution: {execution[0].get('kind', '')}: "
            f"{execution[0].get('text', '')}"
        )
    if deltas:
        parts.append(
            "plan delta: "
            f"{deltas[0].get('change_kind') or 'plan'} | "
            f"{deltas[0].get('run_plan', '')} vs "
            f"{deltas[0].get('baseline_plan') or 'none'}"
        )
    return " | ".join(parts) or "none"


def _cognition_outcomes_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Cognition Outcome Evaluation</h2>"
        "<p>Post-decision metric deltas against the deterministic rule baseline "
        "for accepted or blocked generated cognition calls.</p>"
        f"{_cognition_outcomes_table(items)}"
        "</section>"
    )


def _cognition_outcomes_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        final = (item.get("windows") or [{}])[-1]
        deltas = final.get("deltas") or {}
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['agent_name'])}</td>"
            f"<td>{escape(item.get('cognition_signal') or '')}</td>"
            f"<td>{escape(item.get('outcome_signal') or '')}</td>"
            f"<td>{escape(final.get('label') or '')}</td>"
            f"<td>{escape(_signed_number(deltas.get('average_need', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('average_trust', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('institutional_cohesion', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('food', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('materials', 0)))}</td>"
            f"<td>{escape(_signed_number(deltas.get('shelter', 0)))}</td>"
            f"<td>{escape(_cognition_outcome_windows_text(item))}</td>"
            f"<td>{escape(item.get('summary') or '')}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Cognition Signal</th><th>Outcome Signal</th><th>Final Window</th><th>Avg Need</th><th>Trust</th><th>Cohesion</th><th>Food</th><th>Materials</th><th>Shelter</th><th>Windows</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _cognition_outcome_windows_text(item: dict[str, Any]) -> str:
    parts = []
    for window in item.get("windows") or []:
        deltas = window.get("deltas") or {}
        parts.append(
            f"{window.get('label', '')}: "
            f"need {_signed_number(deltas.get('average_need', 0))}, "
            f"trust {_signed_number(deltas.get('average_trust', 0))}, "
            f"food {_signed_number(deltas.get('food', 0))}"
        )
    return " | ".join(parts) or "none"


def _choice_tension_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Choice Tension Evaluation</h2>"
        "<p>Generated cognition calls where social history, observer intent, "
        "and resource pressure pull toward different actions.</p>"
        f"{_choice_tension_table(items)}"
        "</section>"
    )


def _choice_tension_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item.get('day', '')}</td>"
            f"<td>{escape(str(item.get('agent_name', '')))}</td>"
            f"<td>{escape(str(item.get('signal', '')))}</td>"
            f"<td>{escape(str(item.get('baseline_action') or 'none'))}</td>"
            f"<td>{escape(str(item.get('used_action') or 'none'))}</td>"
            f"<td>{escape(', '.join(item.get('competing_groups') or []))}</td>"
            f"<td>{escape(', '.join(item.get('mentioned_groups') or []))}</td>"
            f"<td>{escape(', '.join(item.get('observer_intents') or []))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Signal</th><th>Baseline</th><th>Used</th><th>Competing</th><th>Mentioned</th><th>Observer Intent</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _reason_richness_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Reason Richness Evaluation</h2>"
        "<p>Generated cognition reasons scored by concrete evidence groups: "
        "identity, memory, relationship, organization, observer intent, "
        "historical scars, resources, tradeoffs, and specific targets.</p>"
        f"{_reason_richness_table(items)}"
        "</section>"
    )


def _reason_richness_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item.get('day', '')}</td>"
            f"<td>{escape(str(item.get('agent_name', '')))}</td>"
            f"<td>{escape(str(item.get('prompt_version') or 'unknown'))}</td>"
            f"<td>{escape(str(item.get('signal', '')))}</td>"
            f"<td>{escape(str(item.get('generated_score', 0)))}</td>"
            f"<td>{escape(str(item.get('baseline_score', 0)))}</td>"
            f"<td>{escape(', '.join(item.get('generated_groups') or []))}</td>"
            f"<td>{escape(', '.join(item.get('baseline_groups') or []))}</td>"
            f"<td>{escape(str(item.get('action_changed', False)))}</td>"
            f"<td>{escape(str(item.get('target_changed', False)))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Prompt</th><th>Signal</th><th>Generated</th><th>Baseline</th><th>Generated Groups</th><th>Baseline Groups</th><th>Action</th><th>Target</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _reflection_trace_section(trace: list[dict[str, Any]]) -> str:
    if not trace:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Reflection Trace</h2>"
        f"<p>{escape(_reflection_trace_summary(trace))}</p>"
        f"{_reflection_trace_table(trace)}"
        "</section>"
    )


def _reflection_trace_table(trace: list[dict[str, Any]]) -> str:
    rows = []
    for item in trace[-30:]:
        memory_refs = ", ".join(str(ref) for ref in item.get("memory_refs", []))
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['agent_name'])}</td>"
            f"<td>{escape(item['status'])}</td>"
            f"<td>{escape(item.get('focus') or '')}</td>"
            f"<td>{escape(memory_refs or 'none')}</td>"
            f"<td>{escape(item.get('proposed_reflection') or 'none')}</td>"
            f"<td>{escape(item.get('baseline_reflection') or '')}</td>"
            f"<td>{escape(item.get('used_reflection') or '')}</td>"
            f"<td>{escape(str(item.get('error') or ''))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Status</th><th>Focus</th><th>Memory refs</th><th>Codex Reflection</th><th>Rule Baseline</th><th>Used</th><th>Error</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _reflection_follow_through_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Reflection Follow-through</h2>"
        "<p>Downstream plans, dialogue, and rule-baseline differences after "
        "accepted generated reflections.</p>"
        f"{_reflection_follow_through_table(items)}"
        "</section>"
    )


def _reflection_follow_through_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['agent_name'])}</td>"
            f"<td>{escape(item.get('focus') or '')}</td>"
            f"<td>{escape(item.get('signal') or '')}</td>"
            f"<td>{item['window_start']}-{item['window_end']}</td>"
            f"<td>{len(item.get('plan_evidence') or [])}</td>"
            f"<td>{len(item.get('dialogue_evidence') or [])}</td>"
            f"<td>{len(item.get('baseline_plan_deltas') or [])}</td>"
            f"<td>{escape(_follow_through_evidence_text(item))}</td>"
            f"<td>{escape(item.get('summary') or '')}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Focus</th><th>Signal</th><th>Window</th><th>Plan evidence</th><th>Dialogue evidence</th><th>Baseline plan deltas</th><th>Evidence sample</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _follow_through_evidence_text(item: dict[str, Any]) -> str:
    parts = []
    plans = item.get("plan_evidence") or []
    dialogues = item.get("dialogue_evidence") or []
    deltas = item.get("baseline_plan_deltas") or []
    if plans:
        parts.append(f"plan: {plans[0].get('text', '')}")
    if dialogues:
        parts.append(f"dialogue: {dialogues[0].get('text', '')}")
    if deltas:
        parts.append(
            "baseline delta: "
            f"{deltas[0].get('change_kind') or 'plan'} | "
            f"{deltas[0].get('run_plan', '')} vs {deltas[0].get('baseline_plan') or 'none'}"
        )
    return " | ".join(parts) or "none"


def _dialogue_trace_section(trace: list[dict[str, Any]]) -> str:
    if not trace:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Dialogue Trace</h2>"
        f"<p>{escape(_dialogue_trace_summary(trace))}</p>"
        f"{_dialogue_trace_table(trace)}"
        "</section>"
    )


def _dialogue_trace_table(trace: list[dict[str, Any]]) -> str:
    rows = []
    for item in trace[-30:]:
        memory_refs = ", ".join(str(ref) for ref in item.get("memory_refs", []))
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['speaker_name'])}</td>"
            f"<td>{escape(item['partner_name'])}</td>"
            f"<td>{escape(item['status'])}</td>"
            f"<td>{escape(item.get('focus') or '')}</td>"
            f"<td>{escape(memory_refs or 'none')}</td>"
            f"<td>{escape(item.get('proposed_dialogue') or 'none')}</td>"
            f"<td>{escape(item.get('baseline_dialogue') or '')}</td>"
            f"<td>{escape(item.get('used_dialogue') or '')}</td>"
            f"<td>{escape(str(item.get('error') or ''))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Speaker</th><th>Partner</th><th>Status</th><th>Focus</th><th>Memory refs</th><th>Codex Dialogue</th><th>Rule Baseline</th><th>Used</th><th>Error</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _dialogue_follow_through_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Dialogue Follow-through</h2>"
        "<p>Downstream memory, reflection, plan, and rule-baseline differences "
        "after accepted generated dialogues.</p>"
        f"{_dialogue_follow_through_table(items)}"
        "</section>"
    )


def _dialogue_follow_through_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['speaker_name'])}</td>"
            f"<td>{escape(item['partner_name'])}</td>"
            f"<td>{escape(item.get('focus') or '')}</td>"
            f"<td>{escape(item.get('signal') or '')}</td>"
            f"<td>{item['window_start']}-{item['window_end']}</td>"
            f"<td>{len(item.get('memory_evidence') or [])}</td>"
            f"<td>{len(item.get('reflection_evidence') or [])}</td>"
            f"<td>{len(item.get('plan_evidence') or [])}</td>"
            f"<td>{len(item.get('baseline_reflection_deltas') or [])}</td>"
            f"<td>{len(item.get('baseline_plan_deltas') or [])}</td>"
            f"<td>{escape(_dialogue_follow_evidence_text(item))}</td>"
            f"<td>{escape(item.get('summary') or '')}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Speaker</th><th>Partner</th><th>Focus</th><th>Signal</th><th>Window</th><th>Memory</th><th>Reflection</th><th>Plan</th><th>Reflection deltas</th><th>Plan deltas</th><th>Evidence sample</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _dialogue_follow_evidence_text(item: dict[str, Any]) -> str:
    parts = []
    memories = item.get("memory_evidence") or []
    reflections = item.get("reflection_evidence") or []
    plans = item.get("plan_evidence") or []
    reflection_deltas = item.get("baseline_reflection_deltas") or []
    plan_deltas = item.get("baseline_plan_deltas") or []
    if memories:
        parts.append(f"memory: {memories[0].get('agent_name', '')}: {memories[0].get('text', '')}")
    if reflections:
        parts.append(
            f"reflection: {reflections[0].get('agent_name', '')}: "
            f"{reflections[0].get('text', '')}"
        )
    if plans:
        parts.append(f"plan: {plans[0].get('agent_name', '')}: {plans[0].get('text', '')}")
    if reflection_deltas:
        parts.append(
            "reflection delta: "
            f"{reflection_deltas[0].get('agent_name', '')}: "
            f"{reflection_deltas[0].get('run_text', '')}"
        )
    if plan_deltas:
        parts.append(
            "plan delta: "
            f"{plan_deltas[0].get('change_kind') or 'plan'} | "
            f"{plan_deltas[0].get('agent_name', '')}: "
            f"{plan_deltas[0].get('run_text', '')}"
        )
    return " | ".join(parts) or "none"


def _generated_chains_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Generated Chain Evaluation</h2>"
        "<p>Accepted generated dialogue linked to accepted generated reflection "
        "and later plans.</p>"
        f"{_generated_chains_table(items)}"
        "</section>"
    )


def _generated_chains_table(items: list[dict[str, Any]]) -> str:
    rows = []
    for item in items[-20:]:
        rows.append(
            "<tr>"
            f"<td>{item['dialogue_day']} -> {item['reflection_day']}</td>"
            f"<td>{escape(item['speaker_name'])} / {escape(item['partner_name'])}</td>"
            f"<td>{escape(item['reflection_agent_name'])}</td>"
            f"<td>{escape(item.get('dialogue_focus') or '')}</td>"
            f"<td>{escape(item.get('reflection_focus') or '')}</td>"
            f"<td>{escape(item.get('signal') or '')}</td>"
            f"<td>{escape(', '.join(item.get('shared_terms') or []) or 'none')}</td>"
            f"<td>{len(item.get('memory_evidence') or [])}</td>"
            f"<td>{len(item.get('plan_evidence') or [])}</td>"
            f"<td>{len(item.get('baseline_plan_deltas') or [])}</td>"
            f"<td>{escape(_generated_chain_evidence_text(item))}</td>"
            f"<td>{escape(item.get('summary') or '')}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Days</th><th>Dialogue</th><th>Reflection Agent</th><th>Dialogue Focus</th><th>Reflection Focus</th><th>Signal</th><th>Shared Terms</th><th>Memory</th><th>Plan</th><th>Plan deltas</th><th>Evidence sample</th><th>Summary</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _generated_chain_evidence_text(item: dict[str, Any]) -> str:
    parts = []
    memories = item.get("memory_evidence") or []
    plans = item.get("plan_evidence") or []
    deltas = item.get("baseline_plan_deltas") or []
    if memories:
        parts.append(f"memory: {memories[0].get('text', '')}")
    if plans:
        parts.append(f"plan: {plans[0].get('text', '')}")
    if deltas:
        parts.append(
            "baseline delta: "
            f"{deltas[0].get('change_kind') or 'plan'} | "
            f"{deltas[0].get('run_plan', '')}"
        )
    return " | ".join(parts) or "none"


def _baseline_comparison_section(comparison: dict[str, Any] | None) -> str:
    if not comparison:
        return ""
    return (
        "<section class=\"band\">"
        "<h2>Rule Baseline Comparison</h2>"
        f"<p>{escape(str(comparison.get('summary', '')))}</p>"
        f"{_baseline_delta_table(comparison.get('deltas', {}))}"
        f"{_baseline_finding_text(comparison)}"
        "</section>"
    )


def _baseline_delta_table(deltas: dict[str, Any]) -> str:
    if not deltas:
        return "<p>No metric deltas recorded.</p>"
    rows = []
    for key in COMPARISON_METRICS:
        if key not in deltas:
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(key)}</td>"
            f"<td>{escape(_signed_number(deltas[key]))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Metric</th><th>Run minus rule baseline</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _baseline_finding_text(comparison: dict[str, Any]) -> str:
    findings = comparison.get("baseline_findings", [])
    social = comparison.get("baseline_social_findings", [])
    finding_codes = ", ".join(item.get("code", "") for item in findings) or "none"
    social_codes = ", ".join(item.get("code", "") for item in social) or "none"
    return (
        f"<p>Rule baseline health: {escape(finding_codes)}; "
        f"social: {escape(social_codes)}.</p>"
    )


def _plan_summary(plan: dict[str, Any]) -> str:
    if not plan:
        return "none"
    target = f" -> {plan['target_id']}" if plan.get("target_id") else ""
    return f"{plan.get('action', 'none')}{target}: {plan.get('reason', '')}"


def _counterfactual_summary(item: dict[str, Any]) -> str:
    if not item:
        return "none"
    baseline = item.get("baseline") or {}
    proposed = item.get("proposed") or {}
    return (
        f"{item.get('recommendation', 'unknown')} "
        f"delta {_signed_number(item.get('score_delta', 0))}; "
        f"baseline {baseline.get('score', 0)} vs proposed {proposed.get('score', 0)}"
    )


def _cognition_trace_summary(trace: list[dict[str, Any]]) -> str:
    calls = len(trace)
    accepted = sum(1 for item in trace if item.get("status") == "primary")
    policy_fallbacks = sum(
        1
        for item in trace
        if item.get("status") in {"baseline_after_policy", "baseline_after_counterfactual"}
    )
    failures = calls - accepted - policy_fallbacks
    diverged = sum(1 for item in trace if item.get("diverged_from_baseline"))
    rest_overrides = sum(
        1
        for item in trace
        if (item.get("used_plan") or {}).get("action") == "rest"
        and (item.get("baseline_plan") or {}).get("action") != "rest"
    )
    divergence_rate = diverged / calls if calls else 0.0
    return (
        f"calls {calls}; accepted {accepted}; policy fallbacks {policy_fallbacks}; "
        f"failures {failures}; "
        f"divergence rate {divergence_rate:.0%}; rest overrides {rest_overrides}."
    )


def _reflection_trace_summary(trace: list[dict[str, Any]]) -> str:
    calls = len(trace)
    accepted = sum(1 for item in trace if item.get("status") == "primary")
    failures = calls - accepted
    grounded = sum(1 for item in trace if item.get("memory_refs"))
    return (
        f"calls {calls}; accepted {accepted}; failures {failures}; "
        f"memory grounded {grounded}."
    )


def _dialogue_trace_summary(trace: list[dict[str, Any]]) -> str:
    calls = len(trace)
    accepted = sum(1 for item in trace if item.get("status") == "primary")
    failures = calls - accepted
    grounded = sum(1 for item in trace if item.get("memory_refs"))
    return (
        f"calls {calls}; accepted {accepted}; failures {failures}; "
        f"memory grounded {grounded}."
    )


def _comparison_summary(deltas: dict[str, float]) -> str:
    need_delta = deltas.get("average_need", 0.0)
    trust_delta = deltas.get("average_trust", 0.0)
    cohesion_delta = deltas.get("institutional_cohesion", 0.0)
    crisis_delta = deltas.get("crisis_events", 0.0)
    return (
        "Compared with the deterministic rule baseline: "
        f"average need {_signed_number(need_delta)}, "
        f"trust {_signed_number(trust_delta)}, "
        f"institutional cohesion {_signed_number(cohesion_delta)}, "
        f"crisis events {_signed_number(crisis_delta)}."
    )


def _signed_number(value: Any) -> str:
    number = float(value)
    if number > 0:
        return f"+{number:g}"
    return f"{number:g}"


def _percent(value: Any) -> str:
    return f"{float(value) * 100:.0f}%"


def _experiment_table(reports: list[dict[str, Any]]) -> str:
    rows = []
    for report in reports:
        final = report["final_metrics"]
        finding_codes = ", ".join(item["code"] for item in report["findings"])
        need_pct = max(0, min(100, int(final["average_need"] * 100)))
        trust_pct = max(0, min(100, int(final["average_trust"] * 100)))
        reputation_pct = max(0, min(100, int(final["average_reputation"] * 100)))
        cohesion_pct = max(0, min(100, int(final["institutional_cohesion"] * 100)))
        rows.append(
            "<tr>"
            f"<td>{report['seed']}</td>"
            f"<td>{final['population']}</td>"
            f"<td>{final['food']}</td>"
            f"<td><div class=\"bar\"><span style=\"width:{need_pct}%\"></span></div>{final['average_need']}</td>"
            f"<td><div class=\"bar\"><span style=\"width:{trust_pct}%\"></span></div>{final['average_trust']}</td>"
            f"<td><div class=\"bar\"><span style=\"width:{reputation_pct}%\"></span></div>{final['average_reputation']}</td>"
            f"<td><div class=\"bar\"><span style=\"width:{cohesion_pct}%\"></span></div>{final['institutional_cohesion']}</td>"
            f"<td>{escape(finding_codes)}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Seed</th><th>Pop</th><th>Food</th><th>Need</th><th>Trust</th><th>Rep</th><th>Cohesion</th><th>Findings</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _metric_tile(label: str, value: Any) -> str:
    return f"<div class=\"metric\"><label>{escape(label)}</label><strong>{escape(str(value))}</strong></div>"


def _resources_text(resources: dict[str, Any]) -> str:
    return ", ".join(
        f"{key}:{value}"
        for key, value in sorted(resources.items())
        if abs(float(value)) > 0.001
    ) or "empty"


def _latest_reflection(agent: dict[str, Any]) -> str:
    reflections = agent.get("recent_reflections") or []
    if reflections:
        return str(reflections[-1])
    memories = agent.get("recent_memory_stream") or []
    if memories:
        return str(memories[-1].get("text", ""))
    return ""


def _latest_life_episode(agent: dict[str, Any]) -> str:
    entries = agent.get("recent_life_journal") or []
    if not entries:
        return "No daily life journal yet."
    latest = entries[-1]
    mood = str(latest.get("mood", "steady"))
    summary = str(latest.get("summary", ""))
    return f"{mood}: {summary}" if summary else mood


def _short_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _finding_badge(finding: dict[str, Any]) -> str:
    severity = escape(finding["severity"])
    text = escape(f"{finding['code']}: {finding['description']}")
    return f"<span class=\"badge {severity}\">{text}</span>"


def _social_finding_badge(finding: dict[str, Any]) -> str:
    severity = escape(finding["severity"])
    text = escape(f"{finding['code']}: {finding['description']}")
    return f"<span class=\"badge {severity}\">{text}</span>"


def _finding_summary(findings: list[dict[str, Any]]) -> str:
    if any(item["severity"] == "critical" for item in findings):
        return "Critical"
    if any(item["severity"] == "warning" for item in findings):
        return "Warning"
    return "Stable"


def _experiment_summary(reports: list[dict[str, Any]]) -> str:
    critical = sum(
        1
        for report in reports
        if any(item["severity"] == "critical" for item in report["findings"])
    )
    warning = sum(
        1
        for report in reports
        if any(item["severity"] == "warning" for item in report["findings"])
    )
    return f"{critical} critical · {warning} warning"


def _route_key(first_location_id: str, second_location_id: str) -> str:
    left, right = sorted([first_location_id, second_location_id])
    return f"{left}|{right}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
