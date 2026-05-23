from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from .health import HealthFinding, RunReport
from .model import Metrics, WorldState
from .social_evaluation import SocialFinding, assess_social_dynamics


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
    reflection_trace: list[dict[str, Any]] | None = None,
    reflection_follow_through: list[dict[str, Any]] | None = None,
    dialogue_trace: list[dict[str, Any]] | None = None,
    dialogue_follow_through: list[dict[str, Any]] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    social_findings = assess_social_dynamics(world)
    record = {
        "kind": "run",
        "generated_at": _now(),
        "seed": seed,
        "days": metrics[-1].day if metrics else world.day,
        "metrics": [asdict(item) for item in metrics],
        "final_metrics": asdict(metrics[-1]) if metrics else None,
        "findings": [asdict(item) for item in findings],
        "social_findings": [item.as_dict() for item in social_findings],
        "resources": dict(world.resources),
        "route_loads": {
            key: round(value, 3)
            for key, value in world.route_loads.items()
        },
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "location_id": agent.location_id,
                "profile": asdict(agent.profile),
                "needs": asdict(agent.needs),
                "average_need": round(agent.needs.average(), 3),
                "average_trust": _average(agent.relationships.values()),
                "reputation": round(agent.reputation, 3),
                "organization_ids": list(agent.organization_ids),
                "active_plan": _plan_dict(agent.active_plan),
                "recent_memories": agent.memories[-5:],
                "recent_memory_stream": [
                    asdict(memory)
                    for memory in agent.memory_stream[-5:]
                ],
                "recent_reflections": agent.reflections[-3:],
            }
            for agent in world.agents
        ],
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
            }
            for location in world.locations
        ],
        "events": [asdict(event) for event in world.event_log],
    }
    if history is not None:
        record["history"] = history
    if cognition_trace is not None:
        record["cognition_trace"] = cognition_trace
    if reflection_trace is not None:
        record["reflection_trace"] = reflection_trace
    if reflection_follow_through is not None:
        record["reflection_follow_through"] = reflection_follow_through
    if dialogue_trace is not None:
        record["dialogue_trace"] = dialogue_trace
    if dialogue_follow_through is not None:
        record["dialogue_follow_through"] = dialogue_follow_through
    if baseline_comparison is not None:
        record["baseline_comparison"] = baseline_comparison
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


def write_json(path: str | Path, data: dict[str, Any] | list[Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html(path: str | Path, html: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def render_run_html(record: dict[str, Any]) -> str:
    metrics = record["metrics"]
    final = record["final_metrics"] or {}
    findings = record["findings"]
    social_findings = record.get("social_findings", [])
    cognition_trace = record.get("cognition_trace", [])
    reflection_trace = record.get("reflection_trace", [])
    reflection_follow_through = record.get("reflection_follow_through", [])
    dialogue_trace = record.get("dialogue_trace", [])
    dialogue_follow_through = record.get("dialogue_follow_through", [])
    baseline_comparison = record.get("baseline_comparison")
    agents = record["agents"]
    organizations = record.get("organizations", [])
    locations = record.get("locations", [])
    history = record.get("history")
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
    <section class="band">
      <h2>Health</h2>
      <div class="finding-row">{''.join(_finding_badge(item) for item in findings)}</div>
    </section>
    <section class="band">
      <h2>Social Evaluation</h2>
      <div class="finding-row">{''.join(_social_finding_badge(item) for item in social_findings)}</div>
    </section>
    {_cognition_trace_section(cognition_trace)}
    {_reflection_trace_section(reflection_trace)}
    {_reflection_follow_through_section(reflection_follow_through)}
    {_dialogue_trace_section(dialogue_trace)}
    {_dialogue_follow_through_section(dialogue_follow_through)}
    {_baseline_comparison_section(baseline_comparison)}
    {_history_section(history)}
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
h1, h2 { margin: 0; letter-spacing: 0; }
h1 { font-size: clamp(28px, 4vw, 48px); line-height: 1; }
h2 { font-size: 18px; margin-bottom: 12px; }
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
@media (max-width: 900px) {
  .topbar { display: block; }
  .status { text-align: left; margin-top: 10px; }
  .metric-strip { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
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
            "</tr>"
        )
    return "<table><thead><tr><th>Name</th><th>Kind</th><th>Condition</th><th>Cap</th><th>Resources</th><th>Production</th><th>Maint</th><th>Links</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


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
            for kind in ("disaster", "hunger_crisis", "institutional_crisis", "organization", "rationing")
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
        rows.append(
            "<tr>"
            f"<td>{item['day']}</td>"
            f"<td>{escape(item['agent_name'])}</td>"
            f"<td>{escape(item['status'])}</td>"
            f"<td>{escape(_plan_summary(proposed))}</td>"
            f"<td>{escape(_plan_summary(baseline))}</td>"
            f"<td>{escape(_plan_summary(used))}</td>"
            f"<td>{escape(str(item.get('diverged_from_baseline', False)))}</td>"
            f"<td>{escape(str(item.get('error') or ''))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Day</th><th>Agent</th><th>Status</th><th>Codex Plan</th><th>Rule Baseline</th><th>Used</th><th>Diverged</th><th>Error</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


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


def _cognition_trace_summary(trace: list[dict[str, Any]]) -> str:
    calls = len(trace)
    accepted = sum(1 for item in trace if item.get("status") == "primary")
    policy_fallbacks = sum(
        1 for item in trace if item.get("status") == "baseline_after_policy"
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


def _average(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(items) / len(items), 3)


def _plan_dict(plan: Any) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "action": plan.action.value,
        "priority": plan.priority,
        "reason": plan.reason,
        "target_id": plan.target_id,
        "horizon_days": plan.horizon_days,
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
