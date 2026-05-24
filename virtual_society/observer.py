from __future__ import annotations


def render_observer_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Virtual Society Observer</title>
  <style>
:root {
  color-scheme: light;
  --bg: #eef3f2;
  --ink: #17201f;
  --muted: #5b6868;
  --line: #c2cfcc;
  --panel: #ffffff;
  --green: #23785f;
  --blue: #2f5d86;
  --red: #a33232;
  --amber: #a15c12;
  --violet: #6e5792;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
}
.shell { max-width: 1360px; margin: 0 auto; padding: 18px; }
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--ink);
}
h1 { font-size: 24px; margin: 0; letter-spacing: 0; }
h2 { font-size: 15px; margin: 0 0 10px; letter-spacing: 0; }
.status { color: var(--blue); font-weight: 700; text-align: right; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }
button {
  min-height: 36px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  border-radius: 6px;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
}
button:hover { border-color: var(--blue); color: var(--blue); }
button.danger:hover { border-color: var(--red); color: var(--red); }
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.metric {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  min-height: 74px;
}
.metric label { display: block; color: var(--muted); font-size: 12px; }
.metric strong { display: block; font-size: 24px; margin-top: 5px; }
.grid { display: grid; grid-template-columns: minmax(520px, 1.2fr) minmax(380px, 0.8fr); gap: 12px; }
.band {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 14px;
  min-width: 0;
}
.society-map {
  position: relative;
  min-height: 430px;
  border: 1px solid var(--line);
  background:
    linear-gradient(90deg, rgba(47,93,134,0.08) 1px, transparent 1px),
    linear-gradient(0deg, rgba(47,93,134,0.08) 1px, transparent 1px),
    #fbfdfc;
  background-size: 36px 36px;
  overflow: hidden;
}
.agent-node {
  position: absolute;
  width: 94px;
  min-height: 72px;
  transform: translate(-50%, -50%);
  border: 2px solid var(--blue);
  border-radius: 6px;
  background: #ffffff;
  padding: 7px;
  box-shadow: 0 4px 14px rgba(23,32,31,0.12);
}
.agent-node.low { border-color: var(--amber); }
.agent-node strong { display: block; font-size: 13px; overflow-wrap: anywhere; }
.agent-node span { display: block; color: var(--muted); font-size: 11px; margin-top: 2px; overflow-wrap: anywhere; }
.org-row { display: grid; grid-template-columns: 1fr 70px 70px; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--line); }
.event-row { display: grid; grid-template-columns: 42px 92px 1fr; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.scar-row { grid-template-columns: 100px 1fr 120px; }
.event-row span, .org-row span { overflow-wrap: anywhere; }
.muted { color: var(--muted); }
.chart { width: 100%; height: 180px; border: 1px solid var(--line); background: #fbfdfc; display: block; }
@media (max-width: 980px) {
  .topbar { display: block; }
  .status { text-align: left; margin-top: 8px; }
  .grid { grid-template-columns: 1fr; }
  .society-map { min-height: 360px; }
}
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <h1>Virtual Society Observer</h1>
      <div id="status" class="status">Connecting</div>
    </header>
    <section class="controls" aria-label="Controls">
      <button id="step1">Step 1 Day</button>
      <button id="step7">Step 7 Days</button>
      <button id="food">Add Food</button>
      <button id="hope">Hope Broadcast</button>
      <button id="storm" class="danger">Storm</button>
      <button id="reset" class="danger">Reset</button>
    </section>
    <section id="metrics" class="metric-strip"></section>
    <section class="grid">
      <div class="band">
        <h2>Society Map</h2>
        <div id="map" class="society-map"></div>
      </div>
      <div class="band">
        <h2>Organizations</h2>
        <div id="organizations"></div>
      </div>
      <div class="band">
        <h2>Locations</h2>
        <div id="locations"></div>
      </div>
      <div class="band">
        <h2>Metrics</h2>
        <svg id="chart" class="chart" viewBox="0 0 520 180" role="img" aria-label="Metrics chart"></svg>
      </div>
      <div class="band">
        <h2>Historical Scars</h2>
        <div id="scars"></div>
      </div>
      <div class="band">
        <h2>Recent Events</h2>
        <div id="events"></div>
      </div>
    </section>
  </main>
  <script>
const state = { snapshot: null, metrics: [], busy: false };

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }
  return response.json();
}

async function refresh() {
  const [snapshot, metrics, events] = await Promise.all([
    api("/state"),
    api("/metrics"),
    api("/events?limit=36")
  ]);
  state.snapshot = snapshot;
  state.metrics = metrics.metrics;
  render(snapshot, metrics, events);
}

async function act(action) {
  if (state.busy) return;
  state.busy = true;
  $("status").textContent = "Working";
  try {
    await action();
    await refresh();
  } catch (error) {
    $("status").textContent = "Error";
    console.error(error);
  } finally {
    state.busy = false;
  }
}

function render(snapshot, metricsPayload, eventsPayload) {
  const final = metricsPayload.final_metrics || snapshot.metrics;
  $("status").textContent = `Day ${snapshot.world.day} | seed ${snapshot.seed}`;
  $("metrics").innerHTML = [
    tile("Population", final.population),
    tile("Food", final.food),
    tile("Materials", final.materials),
    tile("Shelter", final.shelter),
    tile("Avg Need", final.average_need),
    tile("Trust", final.average_trust),
    tile("Reputation", final.average_reputation),
    tile("Cohesion", final.institutional_cohesion)
  ].join("");
  renderMap(snapshot.world.agents);
  renderOrganizations(snapshot.world.organizations);
  renderLocations(snapshot.world.locations || []);
  renderScars(snapshot.world);
  renderEvents(eventsPayload.events);
  renderChart(metricsPayload.metrics);
}

function tile(label, value) {
  return `<div class="metric"><label>${escapeHtml(label)}</label><strong>${escapeHtml(String(value))}</strong></div>`;
}

function renderMap(agents) {
  const map = $("map");
  const centerX = 50;
  const centerY = 50;
  const radius = 34;
  map.innerHTML = agents.map((agent, index) => {
    const angle = (Math.PI * 2 * index) / agents.length - Math.PI / 2;
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius;
    const need = averageNeed(agent.needs);
    const plan = agent.active_plan ? agent.active_plan.action : "none";
    const reflection = latestReflection(agent);
    return `<div class="agent-node ${need < 0.5 ? "low" : ""}" style="left:${x}%;top:${y}%">
      <strong>${escapeHtml(agent.name)}</strong>
      <span>${escapeHtml(agent.role)} | ${escapeHtml(plan)}</span>
      <span>${escapeHtml(agent.location_id || "unknown")}</span>
      <span>need ${need.toFixed(3)}</span>
      <span>rep ${Number(agent.reputation).toFixed(3)}</span>
      <span>${escapeHtml(reflection)}</span>
    </div>`;
  }).join("");
}

function renderOrganizations(organizations) {
  $("organizations").innerHTML = organizations.map((organization) => {
    const targets = organization.inventory_targets || {};
    const targetText = Object.entries(targets)
      .map(([key, value]) => `${escapeHtml(key)} ${Number(value).toFixed(1)}`)
      .join(" ");
    return `
      <div class="org-row">
        <span><strong>${escapeHtml(organization.name)}</strong><br><span class="muted">${escapeHtml(organization.kind)} @ ${escapeHtml(organization.home_location_id || "commons")}</span></span>
        <span>${Number(organization.cohesion).toFixed(3)}</span>
        <span>${Number(organization.reputation).toFixed(3)}<br><span class="muted">${targetText}</span></span>
      </div>
    `;
  }).join("");
}

function renderLocations(locations) {
  $("locations").innerHTML = locations.map((location) => {
    const resources = location.resources || {};
    const production = location.production || {};
    const topProduction = Object.entries(production)
      .sort((a, b) => Number(b[1]) - Number(a[1]))
      .slice(0, 2)
      .map(([key, value]) => `${escapeHtml(key)} ${Number(value).toFixed(2)}`)
      .join(" ");
    return `
      <div class="org-row">
        <span><strong>${escapeHtml(location.name)}</strong><br><span class="muted">${escapeHtml(location.kind)}</span></span>
        <span>${Number(location.condition).toFixed(3)}</span>
        <span>F${Number(resources.food || 0).toFixed(1)} M${Number(resources.materials || 0).toFixed(1)}<br><span class="muted">${topProduction}</span></span>
      </div>
    `;
  }).join("");
}

function renderScars(world) {
  const relationshipCrises = Object.entries(world.relationship_crises || {});
  const blockedRoutes = Object.entries(world.blocked_routes || {});
  const fractures = Object.entries(world.organization_fractures || {});
  const rows = [
    ...relationshipCrises.map(([pair, day]) => ["relationship", pair, `since day ${day}`]),
    ...blockedRoutes.map(([route, need]) => ["route", route, `repair ${Number(need).toFixed(2)}`]),
    ...fractures.map(([org, day]) => ["organization", org, `fractured day ${day}`])
  ];
  if (!rows.length) {
    $("scars").innerHTML = `<span class="muted">No active historical scars.</span>`;
    return;
  }
  $("scars").innerHTML = rows.map(([kind, subject, detail]) => `
    <div class="event-row scar-row">
      <span>${escapeHtml(kind)}</span>
      <span>${escapeHtml(subject)}</span>
      <span>${escapeHtml(detail)}</span>
    </div>
  `).join("");
}

function renderEvents(events) {
  $("events").innerHTML = events.slice().reverse().map((event) => `
    <div class="event-row">
      <span>${event.day}</span>
      <span>${escapeHtml(event.kind)}</span>
      <span>${escapeHtml(event.description)}</span>
    </div>
  `).join("");
}

function renderChart(metrics) {
  const svg = $("chart");
  if (!metrics.length) {
    svg.innerHTML = "";
    return;
  }
  const need = metrics.map((item) => Number(item.average_need));
  const trust = metrics.map((item) => Number(item.average_trust));
  const cohesion = metrics.map((item) => Number(item.institutional_cohesion));
  svg.innerHTML = `
    <line x1="18" y1="156" x2="502" y2="156" stroke="#c2cfcc" />
    <line x1="18" y1="18" x2="18" y2="156" stroke="#c2cfcc" />
    <polyline fill="none" stroke="#23785f" stroke-width="3" points="${polyline(need)}" />
    <polyline fill="none" stroke="#2f5d86" stroke-width="3" points="${polyline(trust)}" />
    <polyline fill="none" stroke="#a33232" stroke-width="3" points="${polyline(cohesion)}" />
  `;
}

function polyline(values) {
  const width = 520;
  const height = 180;
  const padding = 18;
  const usableW = width - padding * 2;
  const usableH = height - padding * 2;
  return values.map((value, index) => {
    const x = values.length === 1 ? width / 2 : padding + usableW * index / (values.length - 1);
    const y = height - padding - clamp(value, 0, 1) * usableH;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function averageNeed(needs) {
  return (needs.food + needs.energy + needs.safety + needs.belonging + needs.meaning) / 5;
}

function latestReflection(agent) {
  const reflections = agent.reflections || [];
  if (reflections.length) return reflections[reflections.length - 1];
  const memories = agent.memory_stream || [];
  if (memories.length) return memories[memories.length - 1].text || "";
  return "";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));
}

$("step1").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1 }) })));
$("step7").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 7 }) })));
$("food").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "resource", reason: "observer food aid", params: { resource: "food", amount: 5 } }] }) })));
$("hope").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "broadcast", reason: "observer encouragement", params: { tone: "hope", strength: 0.06, message: "Hold together." } }] }) })));
$("storm").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "disaster", reason: "observer stress test", params: { name: "storm", severity: 0.35 } }] }) })));
$("reset").addEventListener("click", () => act(() => api("/reset", { method: "POST", body: JSON.stringify({ seed: 7 }) })));

refresh();
  </script>
</body>
</html>"""
