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
select {
  min-height: 36px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  border-radius: 6px;
  padding: 8px 10px;
  font-weight: 700;
}
input {
  min-height: 36px;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  border-radius: 6px;
  padding: 8px 10px;
  font-weight: 700;
}
.intent-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}
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
.grid-live { grid-template-columns: minmax(560px, 1.25fr) minmax(410px, 0.75fr); align-items: start; }
.side-stack { display: grid; gap: 12px; }
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
.map-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.route-line { stroke: #91a29e; stroke-width: 6; stroke-linecap: round; opacity: 0.72; }
.route-line.blocked { stroke: var(--red); stroke-dasharray: 10 8; opacity: 0.9; }
.location-node { fill: #ffffff; stroke: var(--blue); stroke-width: 3; }
.location-node.low { stroke: var(--amber); }
.location-node.blocked { stroke: var(--red); }
.location-label { font-size: 12px; font-weight: 700; fill: var(--ink); pointer-events: none; }
.location-meta { font-size: 10px; fill: var(--muted); pointer-events: none; }
.agent-node {
  position: absolute;
  width: 108px;
  min-height: 78px;
  transform: translate(-50%, -50%);
  border: 2px solid var(--blue);
  border-radius: 6px;
  background: #ffffff;
  padding: 7px;
  box-shadow: 0 4px 14px rgba(23,32,31,0.12);
  text-align: left;
  cursor: pointer;
}
.agent-node.low { border-color: var(--amber); }
.agent-node.selected { border-color: var(--green); box-shadow: 0 0 0 3px rgba(35,120,95,0.22), 0 4px 14px rgba(23,32,31,0.12); }
.agent-node strong { display: block; font-size: 13px; overflow-wrap: anywhere; }
.agent-node span { display: block; color: var(--muted); font-size: 11px; margin-top: 2px; overflow-wrap: anywhere; }
.world-pulse {
  display: grid;
  gap: 8px;
}
.pulse-card {
  border-left: 4px solid var(--blue);
  padding-left: 10px;
}
.recommendation {
  border-left: 4px solid var(--green);
  padding: 0 0 8px 10px;
  border-bottom: 1px solid var(--line);
}
.recommendation:last-child { border-bottom: 0; }
.selection-actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.dossier-head {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: start;
}
.dossier-head strong { display: block; font-size: 20px; }
.dossier-meta { color: var(--muted); font-size: 12px; }
.life-timeline { display: grid; gap: 8px; margin-top: 10px; }
.life-entry {
  border-left: 3px solid var(--blue);
  padding-left: 10px;
}
.life-entry strong { display: block; font-size: 13px; }
.relationship-chip {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 8px;
  margin: 4px 4px 0 0;
  font-size: 12px;
}
.relationship-chip.crisis { border-color: var(--red); color: var(--red); }
.org-row { display: grid; grid-template-columns: 1fr 70px 70px; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--line); }
.event-row { display: grid; grid-template-columns: 42px 92px 1fr; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.scar-row { grid-template-columns: 100px 1fr 120px; }
.event-row span, .org-row span { overflow-wrap: anywhere; }
.muted { color: var(--muted); }
.small-list { margin: 6px 0 0; padding-left: 18px; color: var(--muted); font-size: 13px; }
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
      <input id="observerName" value="The Envoy" aria-label="Observer name">
      <button id="step1">Step 1 Day</button>
      <button id="step7">Step 7 Days</button>
      <button id="step30">Step 30 Days</button>
      <button id="food">Add Food</button>
      <button id="hope">Hope Broadcast</button>
      <button id="storm" class="danger">Storm</button>
      <button id="reset" class="danger">Reset</button>
      <button id="resetAlpha" class="danger">Reset Alpha</button>
      <div class="intent-controls" aria-label="Observer intent">
        <select id="intent">
          <option value="repair_routes">Repair Routes</option>
          <option value="reconcile_relationships">Reconcile</option>
          <option value="protect_food">Protect Food</option>
          <option value="coordinate">Coordinate</option>
        </select>
        <select id="intentTarget">
          <option value="selected">Selected Agent</option>
          <option value="all">Everyone</option>
        </select>
        <button id="sendIntent">Send Intent</button>
      </div>
    </section>
    <section id="metrics" class="metric-strip"></section>
    <section class="grid grid-live">
      <div class="band">
        <h2>Society Map</h2>
        <div id="map" class="society-map"></div>
      </div>
      <div class="side-stack">
        <div class="band">
          <h2>World Pulse</h2>
          <div id="worldPulse" class="world-pulse"></div>
        </div>
        <div class="band">
          <h2>Selected Agent</h2>
          <div id="selectedAgent"></div>
        </div>
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
const state = { snapshot: null, report: null, metrics: [], busy: false, selectedAgentId: null, selectedDossier: null };

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
  const [snapshot, metrics, events, report] = await Promise.all([
    api("/state"),
    api("/metrics"),
    api("/events?limit=36"),
    api("/report/run.json")
  ]);
  state.snapshot = snapshot;
  state.report = report;
  state.metrics = metrics.metrics;
  state.selectedDossier = state.selectedAgentId
    ? await api(`/agents/${encodeURIComponent(state.selectedAgentId)}`).catch(() => null)
    : null;
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
  renderMap(snapshot.world);
  renderIntentTarget(snapshot.world.agents);
  renderWorldPulse(state.report);
  renderSelectedAgent(state.selectedDossier);
  renderOrganizations(snapshot.world.organizations);
  renderLocations(snapshot.world.locations || []);
  renderScars(snapshot.world);
  renderEvents(eventsPayload.events);
  renderChart(metricsPayload.metrics);
}

function tile(label, value) {
  return `<div class="metric"><label>${escapeHtml(label)}</label><strong>${escapeHtml(String(value))}</strong></div>`;
}

function renderMap(world) {
  const map = $("map");
  const agents = world.agents || [];
  const locations = world.locations || [];
  const positions = locationPositions(locations);
  const blockedRoutes = new Set(Object.keys(world.blocked_routes || {}));
  const locationById = new Map(locations.map((location) => [location.id, location]));
  const agentsByLocation = new Map();
  for (const agent of agents) {
    const list = agentsByLocation.get(agent.location_id) || [];
    list.push(agent);
    agentsByLocation.set(agent.location_id, list);
  }
  const routes = [];
  const seenRoutes = new Set();
  for (const location of locations) {
    for (const targetId of location.connected_location_ids || []) {
      const key = routeKey(location.id, targetId);
      if (seenRoutes.has(key) || !positions.has(location.id) || !positions.has(targetId)) continue;
      seenRoutes.add(key);
      const [x1, y1] = positions.get(location.id);
      const [x2, y2] = positions.get(targetId);
      const blocked = blockedRoutes.has(key);
      routes.push(`<line class="route-line${blocked ? " blocked" : ""}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"><title>${escapeHtml(key)}</title></line>`);
    }
  }
  const nodes = locations.map((location) => {
    const [x, y] = positions.get(location.id) || [50, 50];
    const residents = agentsByLocation.get(location.id) || [];
    const hasBlocked = (location.connected_location_ids || []).some((targetId) => blockedRoutes.has(routeKey(location.id, targetId)));
    const nodeClass = [
      "location-node",
      hasBlocked ? "blocked" : "",
      Number(location.condition) < 0.55 ? "low" : ""
    ].filter(Boolean).join(" ");
    return `<g>
      <circle class="${nodeClass}" cx="${x}" cy="${y}" r="${22 + Math.min(8, residents.length * 2)}">
        <title>${escapeHtml(location.name)} | ${escapeHtml(resourcesText(location.resources || {}))}</title>
      </circle>
      <text class="location-label" x="${x}" y="${y + 34}" text-anchor="middle">${escapeHtml(location.name)}</text>
      <text class="location-meta" x="${x}" y="${y + 47}" text-anchor="middle">cond ${Number(location.condition).toFixed(2)} | ${residents.length} agents</text>
    </g>`;
  }).join("");
  const agentNodes = agents.map((agent) => {
    const location = locationById.get(agent.location_id);
    const [baseX, baseY] = positions.get(agent.location_id) || [50, 50];
    const locationAgents = agentsByLocation.get(agent.location_id) || [];
    const index = Math.max(0, locationAgents.findIndex((item) => item.id === agent.id));
    const angle = (Math.PI * 2 * index) / Math.max(1, locationAgents.length);
    const orbit = 8 + Math.min(8, locationAgents.length * 1.2);
    const x = clamp(baseX + Math.cos(angle) * orbit, 8, 92);
    const y = clamp(baseY + Math.sin(angle) * orbit, 10, 90);
    const need = averageNeed(agent.needs);
    const plan = agent.active_plan ? agent.active_plan.action : "none";
    const reflection = latestReflection(agent);
    const classes = [
      "agent-node",
      need < 0.5 ? "low" : "",
      agent.id === state.selectedAgentId ? "selected" : ""
    ].filter(Boolean).join(" ");
    return `<div class="${classes}" data-agent-id="${escapeHtml(agent.id)}" role="button" tabindex="0" style="left:${x}%;top:${y}%">
      <strong>${escapeHtml(agent.name)}</strong>
      <span>${escapeHtml(agent.role)} | ${escapeHtml(plan)}</span>
      <span>${escapeHtml(location ? location.name : agent.location_id || "unknown")}</span>
      <span>need ${need.toFixed(3)}</span>
      <span>rep ${Number(agent.reputation).toFixed(3)}</span>
      <span>${escapeHtml(reflection)}</span>
    </div>`;
  }).join("");
  map.innerHTML = `
    <svg class="map-svg" viewBox="0 0 100 100" role="img" aria-label="Live settlement map">
      ${routes.join("")}
      ${nodes}
    </svg>
    ${agentNodes}
  `;
}

function locationPositions(locations) {
  const ids = locations.map((location) => location.id);
  const positions = new Map();
  const center = [50, 50];
  const outer = ids.filter((id) => id !== "commons");
  if (ids.includes("commons")) {
    positions.set("commons", center);
  }
  const ring = ids.includes("commons") ? outer : ids;
  ring.forEach((id, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(1, ring.length) - Math.PI / 2;
    positions.set(id, [
      Number((50 + Math.cos(angle) * 34).toFixed(1)),
      Number((50 + Math.sin(angle) * 34).toFixed(1))
    ]);
  });
  return positions;
}

function routeKey(first, second) {
  return [first, second].sort().join("|");
}

function resourcesText(resources) {
  const items = Object.entries(resources)
    .filter(([, value]) => Math.abs(Number(value)) > 0.001)
    .map(([key, value]) => `${key}:${Number(value).toFixed(2)}`);
  return items.join(", ") || "empty";
}

function renderIntentTarget(agents) {
  if (state.selectedAgentId && !agents.some((agent) => agent.id === state.selectedAgentId)) {
    state.selectedAgentId = null;
  }
  const target = $("intentTarget");
  const selected = agents.find((agent) => agent.id === state.selectedAgentId);
  target.options[0].textContent = selected ? selected.name : "Selected Agent";
}

function renderWorldPulse(report) {
  const final = report?.final_metrics || {};
  const scars = report?.historical_scars || {};
  const chronicle = report?.social_chronicle || {};
  const recommendations = report?.observer_recommendations || [];
  const entries = (chronicle.entries || []).slice(-3);
  const pulseItems = entries.length
    ? entries.map((entry) => {
        const summary = String(entry.summary || entry.title || "");
        const prefix = `Day ${entry.day}:`;
        return `<li>${escapeHtml(summary.startsWith(prefix) ? summary : `${prefix} ${summary}`)}</li>`;
      }).join("")
    : `<li>No social chronicle entries yet.</li>`;
  const recs = recommendations.length
    ? recommendations.slice(0, 4).map((item) => {
        const intervention = item.intervention || {};
        return `<div class="recommendation">
          <strong>${escapeHtml(item.title || "Recommendation")}</strong>
          <p>${escapeHtml(item.expected_effect || "")}</p>
          <span class="muted">${escapeHtml(intervention.kind || "")} day ${escapeHtml(intervention.day || "")}</span>
        </div>`;
      }).join("")
    : `<span class="muted">No concrete observer recommendation is active.</span>`;
  $("worldPulse").innerHTML = `
    <div class="pulse-card">
      <strong>Day ${escapeHtml(report?.days ?? state.snapshot?.world?.day ?? 0)}</strong>
      <p>Need ${escapeHtml(final.average_need ?? "n/a")}, trust ${escapeHtml(final.average_trust ?? "n/a")}, cohesion ${escapeHtml(final.institutional_cohesion ?? "n/a")}.</p>
      <p>${(scars.relationship_crises || []).length} relationship scars, ${(scars.blocked_routes || []).length} blocked routes.</p>
      <ul class="small-list">${pulseItems}</ul>
    </div>
    <div>
      <h2>Observer Next Moves</h2>
      ${recs}
    </div>
  `;
}

function renderSelectedAgent(dossier) {
  if (!state.selectedAgentId) {
    $("selectedAgent").innerHTML = `<span class="muted">Click an agent on the map to inspect daily life, memory, and relationship pressure.</span>`;
    return;
  }
  if (!dossier) {
    $("selectedAgent").innerHTML = `<span class="muted">Selected agent dossier is loading.</span>`;
    return;
  }
  const agent = dossier.agent;
  const plan = agent.active_plan ? `${agent.active_plan.action}: ${agent.active_plan.reason}` : "none";
  const life = (agent.recent_life_journal || []).slice(-5).reverse();
  const memories = (agent.recent_memory_stream || []).slice(-4).reverse();
  const relationships = (dossier.relationship_links || [])
    .sort((a, b) => Number(a.average_trust) - Number(b.average_trust))
    .slice(0, 6);
  const lifeHtml = life.length
    ? life.map((item) => `<div class="life-entry">
        <strong>Day ${escapeHtml(item.day)} · ${escapeHtml(item.mood)}</strong>
        <p>${escapeHtml(item.summary)}</p>
        <span class="muted">${escapeHtml((item.pressures || []).join(", "))}</span>
      </div>`).join("")
    : `<span class="muted">No life journal yet.</span>`;
  const memoryHtml = memories.length
    ? `<ul class="small-list">${memories.map((item) => `<li>day ${escapeHtml(item.day)} · ${escapeHtml(item.kind)}: ${escapeHtml(shortText(item.text || "", 140))}</li>`).join("")}</ul>`
    : `<span class="muted">No recent memory stream entries.</span>`;
  const relationshipHtml = relationships.length
    ? relationships.map((item) => {
        const other = (item.agents || []).find((name, index) => (item.agent_ids || [])[index] !== agent.id) || "unknown";
        return `<span class="relationship-chip ${item.crisis ? "crisis" : ""}">${escapeHtml(other)} · ${escapeHtml(item.average_trust)} · ${item.crisis ? "crisis" : "open"}</span>`;
      }).join("")
    : `<span class="muted">No relationship evidence yet.</span>`;
  $("selectedAgent").innerHTML = `
    <div class="dossier-head">
      <div>
        <strong>${escapeHtml(agent.name)}</strong>
        <span class="dossier-meta">${escapeHtml(agent.role)} @ ${escapeHtml(agent.location_id)}</span>
      </div>
      <span class="dossier-meta">need ${escapeHtml(agent.average_need)} | trust ${escapeHtml(agent.average_trust)}</span>
    </div>
    <p><strong>Plan:</strong> ${escapeHtml(shortText(plan, 180))}</p>
    <div class="selection-actions">
      <button id="selectedBroadcast">Broadcast Intent</button>
      <button id="selectedMediation">Mediate Crisis</button>
      <button id="selectedFood">Food at Location</button>
    </div>
    <h2>Life Timeline</h2>
    <div class="life-timeline">${lifeHtml}</div>
    <h2>Recent Memory</h2>
    ${memoryHtml}
    <h2>Relationship Pressure</h2>
    <div>${relationshipHtml}</div>
  `;
  $("selectedBroadcast").addEventListener("click", () => act(sendObserverIntent));
  $("selectedMediation").addEventListener("click", () => act(sendSelectedMediation));
  $("selectedFood").addEventListener("click", () => act(() => addResourceAtSelectedLocation("food", 4)));
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
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));
}

function shortText(value, limit) {
  const text = String(value || "").replace(/\\s+/g, " ").trim();
  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 3)).trim()}...`;
}

function selectedTargetIds() {
  if ($("intentTarget").value !== "selected") return [];
  return state.selectedAgentId ? [state.selectedAgentId] : [];
}

function intentMessage(intent) {
  const messages = {
    repair_routes: "Reopen blocked routes before more hauling.",
    reconcile_relationships: "Repair trust before the crisis becomes normal.",
    protect_food: "Protect food security and keep distribution visible.",
    coordinate: "Coordinate openly before small failures become shared crises."
  };
  return messages[intent] || "Coordinate the next response.";
}

function observerActorId() {
  const input = $("observerName");
  const name = (input?.value || "observer").trim() || "observer";
  localStorage.setItem("virtualSocietyObserverName", name);
  return name.replace(/[^a-zA-Z0-9 _-]/g, "").replace(/\\s+/g, "_") || "observer";
}

function sendObserverIntent() {
  const intent = $("intent").value;
  const targetIds = selectedTargetIds();
  const actorId = observerActorId();
  const params = {
    intent,
    tone: "hope",
    strength: 0.10,
    message: intentMessage(intent)
  };
  if (targetIds.length) params.target_agent_ids = targetIds;
  return api("/step", {
    method: "POST",
    body: JSON.stringify({
      days: 1,
      interventions: [{
        kind: "broadcast",
        actor_id: actorId,
        reason: `${actorId} intent ${intent}`,
        params
      }]
    })
  });
}

function sendSelectedMediation() {
  const dossier = state.selectedDossier;
  if (!dossier?.agent) return sendObserverIntent();
  const crisis = (dossier.relationship_links || []).find((item) => item.crisis);
  if (!crisis) return sendObserverIntent();
  const actorId = observerActorId();
  return api("/step", {
    method: "POST",
    body: JSON.stringify({
      days: 1,
      interventions: [{
        kind: "mediation",
        actor_id: actorId,
        reason: `${actorId} mediated ${crisis.pair}`,
        params: {
          target_agent_ids: crisis.agent_ids,
          message: "Name the grievance and rebuild a practical agreement."
        }
      }]
    })
  });
}

function addResourceAtSelectedLocation(resource, amount) {
  const agent = state.selectedDossier?.agent;
  const actorId = observerActorId();
  return api("/step", {
    method: "POST",
    body: JSON.stringify({
      days: 1,
      interventions: [{
        kind: "resource",
        actor_id: actorId,
        reason: `${actorId} supported ${agent?.name || "selected agent"}`,
        params: {
          resource,
          amount,
          location_id: agent?.location_id || "commons"
        }
      }]
    })
  });
}

$("step1").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1 }) })));
$("step7").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 7 }) })));
$("step30").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 30 }) })));
$("food").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "resource", actor_id: observerActorId(), reason: `${observerActorId()} food aid`, params: { resource: "food", amount: 5 } }] }) })));
$("hope").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "broadcast", actor_id: observerActorId(), reason: `${observerActorId()} encouragement`, params: { tone: "hope", strength: 0.06, message: "Hold together." } }] }) })));
$("storm").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "disaster", actor_id: observerActorId(), reason: `${observerActorId()} stress test`, params: { name: "storm", severity: 0.35 } }] }) })));
$("reset").addEventListener("click", () => act(() => api("/reset", { method: "POST", body: JSON.stringify({ seed: 7 }) })));
$("resetAlpha").addEventListener("click", () => act(() => api("/reset", { method: "POST", body: JSON.stringify({ seed: 7, world_preset: "generative_alpha" }) })));
$("sendIntent").addEventListener("click", () => act(sendObserverIntent));
const savedObserverName = localStorage.getItem("virtualSocietyObserverName");
if (savedObserverName) $("observerName").value = savedObserverName;

async function selectAgent(agentId) {
  state.selectedAgentId = agentId;
  renderMap(state.snapshot.world);
  renderIntentTarget(state.snapshot.world.agents);
  renderSelectedAgent(null);
  state.selectedDossier = await api(`/agents/${encodeURIComponent(agentId)}`).catch(() => null);
  renderSelectedAgent(state.selectedDossier);
}

$("map").addEventListener("click", (event) => {
  const node = event.target.closest(".agent-node");
  if (!node) return;
  selectAgent(node.dataset.agentId);
});
$("map").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const node = event.target.closest(".agent-node");
  if (!node) return;
  event.preventDefault();
  selectAgent(node.dataset.agentId);
});

refresh();
  </script>
</body>
</html>"""
