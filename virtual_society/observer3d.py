from __future__ import annotations


def render_observer3d_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Virtual Society 3D Observer</title>
  <style>
:root {
  color-scheme: dark;
  --bg: #111716;
  --ink: #eef5f2;
  --muted: #a9b8b4;
  --line: rgba(226, 238, 234, 0.22);
  --panel: rgba(17, 23, 22, 0.78);
  --green: #4fb58f;
  --blue: #6aa3d8;
  --amber: #d49b4a;
  --red: #d16d6d;
}
* { box-sizing: border-box; }
html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
}
#scene {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  display: block;
}
.hud {
  position: fixed;
  z-index: 10;
  pointer-events: none;
}
.hud-panel {
  pointer-events: auto;
  background: var(--panel);
  border: 1px solid var(--line);
  backdrop-filter: blur(10px);
  border-radius: 6px;
  box-shadow: 0 14px 38px rgba(0, 0, 0, 0.26);
}
.top-left { left: 16px; top: 14px; width: min(520px, calc(100vw - 32px)); padding: 14px; }
.top-right { right: 16px; top: 14px; width: 300px; max-width: calc(100vw - 32px); padding: 14px; }
.bottom-left { left: 16px; bottom: 16px; width: min(560px, calc(100vw - 32px)); padding: 12px; }
.bottom-right { right: 16px; bottom: 16px; width: min(420px, calc(100vw - 32px)); padding: 12px; }
h1 { margin: 0 0 6px; font-size: 20px; letter-spacing: 0; }
h2 { margin: 0 0 10px; font-size: 14px; color: var(--muted); letter-spacing: 0; }
.status { color: var(--muted); font-size: 13px; }
.metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(92px, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.metric {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px;
  min-height: 62px;
}
.metric label { display: block; color: var(--muted); font-size: 11px; }
.metric strong { display: block; margin-top: 4px; font-size: 20px; }
.controls { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
button {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--ink);
  font-weight: 700;
  cursor: pointer;
}
button:hover { border-color: var(--blue); color: var(--blue); }
button.danger:hover { border-color: var(--red); color: var(--red); }
select {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--ink);
  font-weight: 700;
  padding: 8px;
}
input {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--ink);
  font-weight: 700;
  padding: 8px;
}
option { color: #17201f; }
.intent-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}
.intent-controls button { grid-column: 1 / -1; }
.list { display: grid; gap: 7px; max-height: 190px; overflow: auto; }
.row {
  display: grid;
  grid-template-columns: 46px 92px 1fr;
  gap: 8px;
  font-size: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 7px;
}
.row span, .detail span { overflow-wrap: anywhere; }
.detail {
  display: grid;
  gap: 6px;
  font-size: 13px;
  max-height: 56vh;
  overflow: auto;
}
.detail strong { font-size: 17px; }
.selection-actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.life-timeline { display: grid; gap: 8px; margin-top: 4px; }
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
.small-list { margin: 4px 0 0; padding-left: 18px; color: var(--muted); }
.hint { margin-top: 8px; color: var(--muted); font-size: 12px; }
.legend { display: flex; flex-wrap: wrap; gap: 12px; color: var(--muted); font-size: 12px; margin-top: 10px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
@media (max-width: 900px) {
  .top-right { top: auto; bottom: 16px; right: 16px; }
  .bottom-left, .bottom-right { display: none; }
  .metrics { grid-template-columns: repeat(2, minmax(92px, 1fr)); }
}
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "https://unpkg.com/three@0.164.1/build/three.module.js",
        "three/addons/": "https://unpkg.com/three@0.164.1/examples/jsm/"
      }
    }
  </script>
</head>
<body>
  <canvas id="scene" aria-label="3D virtual society observer"></canvas>
  <section class="hud top-left hud-panel">
    <h1>Virtual Society 3D Observer</h1>
    <div id="status" class="status">Connecting</div>
    <div id="metrics" class="metrics"></div>
    <div class="legend">
      <span><i class="dot" style="background:#4fb58f"></i>healthy</span>
      <span><i class="dot" style="background:#d49b4a"></i>strained</span>
      <span><i class="dot" style="background:#d16d6d"></i>crisis</span>
      <span><i class="dot" style="background:#6aa3d8"></i>organization ring</span>
    </div>
  </section>
  <section class="hud top-right hud-panel">
    <h2>Controls</h2>
    <input id="observerName" value="The Envoy" aria-label="Observer name">
    <div class="controls">
      <button id="step1">1 Day</button>
      <button id="step7">7 Days</button>
      <button id="step30">30 Days</button>
      <button id="food">Food</button>
      <button id="hope">Broadcast</button>
      <button id="storm" class="danger">Storm</button>
      <button id="reset" class="danger">Reset</button>
      <button id="resetAlpha" class="danger">Reset Alpha</button>
    </div>
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
    <div class="hint">Click an agent in the scene to inspect current needs, daily life, memories, relationships, and organizations.</div>
  </section>
  <section class="hud bottom-left hud-panel">
    <h2>Social Feed</h2>
    <div id="events" class="list"></div>
  </section>
  <section class="hud bottom-right hud-panel">
    <h2>Selection</h2>
    <div id="detail" class="detail"><span class="status">No agent selected.</span></div>
  </section>
  <script type="module">
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111716);
scene.fog = new THREE.Fog(0x111716, 28, 82);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 120);
camera.position.set(16, 13, 18);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 1.5, 0);
controls.maxPolarAngle = Math.PI * 0.48;
controls.minDistance = 9;
controls.maxDistance = 42;

const root = new THREE.Group();
scene.add(root);
const locationGroup = new THREE.Group();
const routeGroup = new THREE.Group();
const agentGroup = new THREE.Group();
const resourceGroup = new THREE.Group();
const organizationGroup = new THREE.Group();
const eventGroup = new THREE.Group();
root.add(locationGroup, routeGroup, agentGroup, resourceGroup, organizationGroup, eventGroup);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const agentObjects = new Map();
let selectedAgentId = null;
let selectedDossier = null;
let latestFrame = null;
let latestSocialFeed = [];
let busy = false;

const ambient = new THREE.HemisphereLight(0xddeee8, 0x1a2422, 1.7);
scene.add(ambient);
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(11, 18, 8);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
scene.add(sun);

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(15, 96),
  new THREE.MeshStandardMaterial({ color: 0x1c2a27, roughness: 0.92, metalness: 0.02 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
root.add(ground);

const grid = new THREE.GridHelper(34, 34, 0x35534d, 0x263b37);
grid.position.y = 0.012;
root.add(grid);

const center = new THREE.Mesh(
  new THREE.CylinderGeometry(2.1, 2.4, 0.3, 48),
  new THREE.MeshStandardMaterial({ color: 0x2f5d86, roughness: 0.72, metalness: 0.03 })
);
center.position.y = 0.15;
center.receiveShadow = true;
center.castShadow = true;
root.add(center);

const centerBeacon = new THREE.Mesh(
  new THREE.ConeGeometry(0.7, 2.4, 32),
  new THREE.MeshStandardMaterial({ color: 0x6aa3d8, emissive: 0x13334c, roughness: 0.45 })
);
centerBeacon.position.y = 1.55;
centerBeacon.castShadow = true;
root.add(centerBeacon);

function makeLabel(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 384;
  canvas.height = 96;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(17,23,22,0.82)";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = "rgba(238,245,242,0.35)";
  context.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);
  context.fillStyle = "#eef5f2";
  context.textAlign = "center";
  context.textBaseline = "middle";
  let fontSize = 24;
  const maxWidth = canvas.width - 24;
  do {
    context.font = `700 ${fontSize}px Segoe UI, Arial`;
    fontSize -= 1;
  } while (fontSize >= 13 && context.measureText(text).width > maxWidth);
  context.fillText(text, canvas.width / 2, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(3.4, 0.92, 1);
  return sprite;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function refresh() {
  const frame = await api("/client/world-frame");
  latestFrame = frame;
  latestSocialFeed = frame.social_feed || [];
  selectedDossier = selectedAgentId
    ? await api(`/agents/${encodeURIComponent(selectedAgentId)}`).catch(() => null)
    : null;
  renderHud(frame);
  renderScene(frame);
}

async function act(task) {
  if (busy) return;
  busy = true;
  setStatus("Working");
  try {
    await task();
    await refresh();
  } catch (error) {
    console.error(error);
    setStatus("Error");
  } finally {
    busy = false;
  }
}

function renderHud(frame) {
  const metrics = frame.metrics || {};
  const resources = frame.resources || {};
  setStatus(`Day ${frame.day} | seed ${frame.seed} | ${frame.version}`);
  document.getElementById("metrics").innerHTML = [
    tile("Population", metrics.population),
    tile("Food", resources.food),
    tile("Materials", resources.materials),
    tile("Shelter", resources.shelter),
    tile("Avg Need", metrics.average_need),
    tile("Trust", metrics.average_trust),
    tile("Reputation", metrics.average_reputation),
    tile("Cohesion", metrics.institutional_cohesion),
    tile("Provider", providerLabel(frame.provider)),
    tile("Protocol", frame.version)
  ].join("");
  document.getElementById("events").innerHTML = latestSocialFeed.slice().reverse().map((event) => `
    <div class="row">
      <span>${event.day}</span>
      <span>${escapeHtml(event.kind)}</span>
      <span>${escapeHtml(event.summary || event.title || event.description || "")}</span>
    </div>
  `).join("");
  renderIntentTarget(frame.agents || []);
  renderDetail();
}

function renderIntentTarget(agents) {
  if (selectedAgentId && !agents.some((agent) => agent.id === selectedAgentId)) {
    selectedAgentId = null;
  }
  const target = document.getElementById("intentTarget");
  const selected = agents.find((agent) => agent.id === selectedAgentId);
  target.options[0].textContent = selected ? selected.name : "Selected Agent";
}

function renderScene(frame) {
  if (!frame) return;
  clearGroup(agentGroup);
  clearGroup(locationGroup);
  clearGroup(routeGroup);
  clearGroup(resourceGroup);
  clearGroup(organizationGroup);
  clearGroup(eventGroup);
  agentObjects.clear();

  const agents = frame.agents || [];
  const organizations = frame.organizations || [];
  const locationPositions = renderLocations3d(frame.locations || []);
  renderRoutes3d(frame.routes || []);
  agents.forEach((agent, index) => {
    const base = locationPositions.get(agent.location_id) || locationPositions.get("commons") || new THREE.Vector3(0, 0, 0);
    const position = vectorFromFrame(agent.position, base);
    const need = Number(agent.average_need ?? averageNeed(agent.needs || {}));
    const visual = agent.visual || {};
    const material = new THREE.MeshStandardMaterial({
      color: colorValue(visual.color, colorForNeed(need)),
      roughness: 0.58,
      metalness: 0.05,
      emissive: selectedAgentId === agent.id ? 0x244461 : 0x000000,
      emissiveIntensity: selectedAgentId === agent.id ? 0.55 : 0
    });
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.52, 1.5, 24), material);
    body.position.copy(position).add(new THREE.Vector3(0, 0.95, 0));
    body.castShadow = true;
    body.userData.agentId = agent.id;
    body.userData.kind = "agent";
    agentGroup.add(body);

    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.36, 24, 16),
      new THREE.MeshStandardMaterial({ color: 0xeef5f2, roughness: 0.5 })
    );
    head.position.copy(position).add(new THREE.Vector3(0, 1.95, 0));
    head.castShadow = true;
    head.userData.agentId = agent.id;
    head.userData.kind = "agent";
    agentGroup.add(head);

    const platform = new THREE.Mesh(
      new THREE.CylinderGeometry(0.72, 0.72, 0.12, 32),
      new THREE.MeshStandardMaterial({ color: 0x263b37, roughness: 0.9 })
    );
    platform.position.copy(position).add(new THREE.Vector3(0, 0.06, 0));
    platform.receiveShadow = true;
    agentGroup.add(platform);

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.8 + Number(agent.reputation || 0) * 0.22, 0.035, 8, 36),
      new THREE.MeshStandardMaterial({ color: 0x6aa3d8, roughness: 0.5, emissive: 0x0c2539, emissiveIntensity: 0.25 })
    );
    ring.position.copy(position).add(new THREE.Vector3(0, 0.22, 0));
    ring.rotation.x = Math.PI / 2;
    agentGroup.add(ring);

    const label = makeLabel(agent.name);
    label.position.copy(position).add(new THREE.Vector3(0, 2.65 + (index % 2) * 0.25, 0));
    agentGroup.add(label);
    agentObjects.set(agent.id, { body, head, ring, label, agent, angle: index, baseY: body.position.y });
  });

  renderOrganizations3d(organizations, locationPositions);
  renderResources(frame.resources || {});
  renderEventMarkers(latestSocialFeed);
}

function renderLocations3d(locations) {
  const fallback = [
    { id: "commons", name: "Commons", kind: "civic", condition: 0.66, position: {x: 0, y: 0, z: 0} }
  ];
  const items = locations.length ? locations : fallback;
  const positions = new Map();
  items.forEach((location, index) => {
    const fallbackPosition = new THREE.Vector3(Math.cos(index) * 10, 0, Math.sin(index) * 10);
    const position = vectorFromFrame(location.position, fallbackPosition);
    positions.set(location.id, position);
    const condition = Number(location.condition ?? 0.6);
    const visual = location.visual || {};
    const marker = new THREE.Mesh(
      new THREE.CylinderGeometry(1.55, 1.8, 0.18 + condition * 0.24, 48),
      new THREE.MeshStandardMaterial({
        color: colorValue(visual.color, colorForLocation(location.kind)),
        roughness: 0.78,
        transparent: true,
        opacity: 0.42 + condition * 0.25,
        emissive: 0x0c2539,
        emissiveIntensity: 0.08
      })
    );
    marker.position.copy(position).add(new THREE.Vector3(0, 0.12, 0));
    marker.receiveShadow = true;
    locationGroup.add(marker);
    const resources = location.resources || {};
    const production = location.production || {};
    const specialty = Object.entries(production).sort((a, b) => Number(b[1]) - Number(a[1]))[0];
    const specialtyText = specialty ? ` ${specialty[0]}x${Number(specialty[1]).toFixed(1)}` : "";
    const label = makeLabel(`${location.name || location.id}${specialtyText} R${Number(location.resident_count || 0)} F${Number(resources.food || 0).toFixed(1)} M${Number(resources.materials || 0).toFixed(1)}`);
    label.position.copy(position).add(new THREE.Vector3(0, 0.85, 0));
    locationGroup.add(label);
  });
  return positions;
}

function renderRoutes3d(routes) {
  routes.forEach((route) => {
    const points = route.points || [];
    if (points.length < 2) return;
    const start = vectorFromFrame(points[0], new THREE.Vector3(0, 0, 0));
    const end = vectorFromFrame(points[points.length - 1], new THREE.Vector3(0, 0, 0));
    const load = Number(route.load || 0);
    const radius = Number(route.visual?.width || (0.035 + Math.min(load, 7) * 0.012));
    const color = colorValue(route.visual?.color, route.blocked ? 0xd16d6d : (load > 4 ? 0xd49b4a : 0x436f76));
    const material = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.74,
      transparent: true,
      opacity: route.blocked ? 0.78 : 0.34 + Math.min(load, 6) * 0.06,
      emissive: route.blocked ? 0x3b0909 : (load > 4 ? 0x3a2106 : 0x071b1d),
      emissiveIntensity: route.blocked ? 0.36 : (load > 4 ? 0.22 : 0.08)
    });
    const from = start.clone().add(new THREE.Vector3(0, 0.1, 0));
    const to = end.clone().add(new THREE.Vector3(0, 0.1, 0));
    const midpoint = from.clone().add(to).multiplyScalar(0.5);
    const direction = to.clone().sub(from);
    const length = direction.length();
    const routeMesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 12), material);
    routeMesh.position.copy(midpoint);
    routeMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
    routeGroup.add(routeMesh);
    if (route.blocked) {
      const barrier = new THREE.Mesh(
        new THREE.BoxGeometry(0.42, 1.5, 1.9),
        new THREE.MeshStandardMaterial({ color: 0xa33232, roughness: 0.58, emissive: 0x330606, emissiveIntensity: 0.35 })
      );
      barrier.position.copy(midpoint).add(new THREE.Vector3(0, 0.9, 0));
      barrier.lookAt(to);
      barrier.castShadow = true;
      routeGroup.add(barrier);
    }
  });
}

function renderOrganizations3d(organizations, locationPositions) {
  organizations.forEach((organization, index) => {
    const home = locationPositions.get(organization.home_location_id) || new THREE.Vector3(0, 0, 0);
    const radius = 1.9 + Math.min(index, 3) * 0.32;
    const visual = organization.visual || {};
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(radius, 0.035 + organization.cohesion * 0.035, 8, 96),
      new THREE.MeshStandardMaterial({
        color: colorValue(visual.color, organization.fractured ? 0xd16d6d : 0x6aa3d8),
        roughness: 0.55,
        transparent: true,
        opacity: 0.28 + organization.cohesion * 0.18,
        emissive: 0x0c2539,
        emissiveIntensity: 0.2
      })
    );
    ring.position.copy(home).add(new THREE.Vector3(0, 0.08 + index * 0.035, 0));
    ring.rotation.x = Math.PI / 2;
    organizationGroup.add(ring);
    const label = makeLabel(organization.name || organization.id);
    label.position.copy(home).add(new THREE.Vector3(0, 1.6 + index * 0.15, 0));
    organizationGroup.add(label);
  });
}

function renderResources(resources) {
  const specs = [
    ["food", resources.food, -4.0, 0x4fb58f],
    ["materials", resources.materials, 0.0, 0xd49b4a],
    ["shelter", resources.shelter, 4.0, 0x6aa3d8]
  ];
  specs.forEach(([name, value, x, color]) => {
    const height = Math.max(0.35, Math.min(5.2, Number(value) / 5));
    const tower = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, height, 0.9),
      new THREE.MeshStandardMaterial({ color, roughness: 0.52, metalness: 0.05 })
    );
    tower.position.set(x, height / 2, -12.2);
    tower.castShadow = true;
    resourceGroup.add(tower);
    const label = makeLabel(`${name} ${Number(value).toFixed(1)}`);
    label.position.set(x, height + 0.95, -12.2);
    resourceGroup.add(label);
  });
}

function renderEventMarkers(events) {
  const importantKinds = ["disaster", "hunger_crisis", "institutional_crisis", "organization", "broadcast", "intervention", "dialogue", "observer_intent", "relationship"];
  const important = events.filter((event) => importantKinds.includes(String(event.kind || ""))).slice(-10);
  important.forEach((event, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(important.length, 1);
    const marker = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.24, 1),
      new THREE.MeshStandardMaterial({ color: colorForEvent(event.kind), roughness: 0.4, emissive: colorForEvent(event.kind), emissiveIntensity: 0.18 })
    );
    marker.position.set(Math.cos(angle) * 12.4, 0.8 + index * 0.04, Math.sin(angle) * 12.4);
    marker.castShadow = true;
    eventGroup.add(marker);
  });
}

function renderDetail() {
  const detail = document.getElementById("detail");
  if (!latestFrame || !selectedAgentId) {
    detail.innerHTML = `<span class="status">No agent selected.</span>`;
    return;
  }
  const agent = selectedDossier?.agent || (latestFrame.agents || []).find((item) => item.id === selectedAgentId);
  if (!agent) {
    detail.innerHTML = `<span class="status">No agent selected.</span>`;
    return;
  }
  const plan = agent.active_plan ? `${agent.active_plan.action}: ${agent.active_plan.reason}` : "none";
  const profile = agent.profile || {};
  const reflection = latestReflection(agent);
  const life = (agent.recent_life_journal || []).slice(-5).reverse();
  const memories = (agent.recent_memory_stream || []).slice(-4).reverse();
  const fallbackMemory = !memories.length && agent.recent_memory
    ? [{day: latestFrame.day, kind: "memory", text: agent.recent_memory}]
    : [];
  const memoryItems = memories.length ? memories : fallbackMemory;
  const relationships = (selectedDossier?.relationship_links || [])
    .sort((a, b) => Number(a.average_trust) - Number(b.average_trust))
    .slice(0, 6);
  const lifeHtml = life.length
    ? life.map((item) => `<div class="life-entry">
        <strong>Day ${escapeHtml(item.day)} | ${escapeHtml(item.mood)}</strong>
        <span>${escapeHtml(item.summary)}</span>
        <span class="status">${escapeHtml((item.pressures || []).join(", "))}</span>
      </div>`).join("")
    : `<span class="status">No life journal yet. Step the world to create daily life entries.</span>`;
  const memoryHtml = memoryItems.length
    ? `<ul class="small-list">${memoryItems.map((item) => `<li>day ${escapeHtml(item.day)} | ${escapeHtml(item.kind)}: ${escapeHtml(shortText(item.text || "", 140))}</li>`).join("")}</ul>`
    : `<span class="status">No recent memory stream entries.</span>`;
  const relationshipHtml = relationships.length
    ? relationships.map((item) => {
        const other = (item.agents || []).find((name, index) => (item.agent_ids || [])[index] !== agent.id) || "unknown";
        return `<span class="relationship-chip ${item.crisis ? "crisis" : ""}">${escapeHtml(other)} | ${escapeHtml(item.average_trust)} | ${item.crisis ? "crisis" : "open"}</span>`;
      }).join("")
    : `<span class="status">No relationship evidence yet.</span>`;
  const actionsHtml = observerAffordanceActions(selectedDossier);
  detail.innerHTML = `
    <strong>${escapeHtml(agent.name)}</strong>
    <span>${escapeHtml(agent.role)} | ${escapeHtml(agent.id)}</span>
    <span>Need ${averageNeed(agent.needs).toFixed(3)} | Reputation ${Number(agent.reputation).toFixed(3)}</span>
    <span>Food ${Number(agent.needs.food).toFixed(3)} | Energy ${Number(agent.needs.energy).toFixed(3)} | Safety ${Number(agent.needs.safety).toFixed(3)}</span>
    <span>Belonging ${Number(agent.needs.belonging).toFixed(3)} | Meaning ${Number(agent.needs.meaning).toFixed(3)}</span>
    <span>Goals ${escapeHtml((profile.long_term_goals || []).join("; "))}</span>
    <span>Plan ${escapeHtml(plan)}</span>
    <span>Reflection ${escapeHtml(reflection)}</span>
    <span>Organizations ${escapeHtml((agent.organization_ids || []).join(", "))}</span>
    <div class="selection-actions">
      ${actionsHtml}
    </div>
    <h2>Life Timeline</h2>
    <div class="life-timeline">${lifeHtml}</div>
    <h2>Recent Memory</h2>
    ${memoryHtml}
    <h2>Relationship Pressure</h2>
    <div>${relationshipHtml}</div>
  `;
  bindObserverAffordanceActions(detail, selectedDossier);
}

async function selectAgent(agentId) {
  selectedAgentId = agentId;
  selectedDossier = null;
  renderScene(latestFrame);
  renderIntentTarget(latestFrame?.agents || []);
  renderDetail();
  selectedDossier = await api(`/agents/${encodeURIComponent(agentId)}`).catch(() => null);
  renderDetail();
}

function onPointerDown(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(agentGroup.children, false);
  const hit = hits.find((item) => item.object.userData.kind === "agent");
  if (hit) {
    selectAgent(hit.object.userData.agentId);
  }
}

function tile(label, value) {
  return `<div class="metric"><label>${escapeHtml(label)}</label><strong>${escapeHtml(String(value))}</strong></div>`;
}

function vectorFromFrame(position, fallback) {
  if (!position) return fallback.clone();
  return new THREE.Vector3(
    Number(position.x || 0),
    Number(position.y || 0),
    Number(position.z || 0)
  );
}

function averageNeed(needs) {
  return (
    Number(needs.food || 0) +
    Number(needs.energy || 0) +
    Number(needs.safety || 0) +
    Number(needs.belonging || 0) +
    Number(needs.meaning || 0)
  ) / 5;
}

function latestReflection(agent) {
  if (agent.latest_reflection) return agent.latest_reflection;
  const reflections = agent.reflections || [];
  if (reflections.length) return reflections[reflections.length - 1];
  if (agent.recent_memory) return agent.recent_memory;
  const memories = agent.memory_stream || [];
  if (memories.length) return memories[memories.length - 1].text || "";
  return "";
}

function colorValue(value, fallback) {
  return value || fallback;
}

function colorForNeed(need) {
  if (need < 0.42) return 0xd16d6d;
  if (need < 0.62) return 0xd49b4a;
  return 0x4fb58f;
}

function colorForEvent(kind) {
  if (kind === "disaster" || kind.includes("crisis")) return 0xd16d6d;
  if (kind === "organization") return 0x6aa3d8;
  if (kind === "broadcast") return 0x4fb58f;
  return 0xd49b4a;
}

function colorForLocation(kind) {
  if (kind === "farm") return 0x4f8f5f;
  if (kind === "wildland") return 0x6f8c56;
  if (kind === "production") return 0xd49b4a;
  if (kind === "dwelling") return 0x6aa3d8;
  return 0x5b7f78;
}

function clearGroup(group) {
  while (group.children.length) {
    const child = group.children.pop();
    child.traverse?.((object) => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) {
        if (object.material.map) object.material.map.dispose();
        object.material.dispose();
      }
    });
  }
}

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

function resize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function animate(time) {
  requestAnimationFrame(animate);
  const t = time * 0.001;
  centerBeacon.rotation.y = t * 0.45;
  for (const item of agentObjects.values()) {
    const pulse = Math.sin(t * 2.2 + item.angle * 3) * 0.045;
    item.body.position.y = item.baseY + pulse;
    item.head.position.y = item.baseY + 1.0 + pulse;
    item.ring.rotation.z = t * 0.35;
    item.label.position.y = item.baseY + 1.7 + pulse;
  }
  eventGroup.rotation.y = t * 0.08;
  controls.update();
  renderer.render(scene, camera);
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

function providerLabel(status) {
  if (!status) return "unknown";
  if (!status.live_llm_enabled) return "rule";
  return `API ${((status.models || [])[0] || "model")}`;
}

function observerAffordanceActions(dossier) {
  const affordances = dossier?.observer_affordances || [];
  if (!affordances.length) {
    return `
      <button data-fallback-action="broadcast">Broadcast Intent</button>
      <button data-fallback-action="mediation">Mediate Crisis</button>
      <button data-fallback-action="food">Food at Location</button>
    `;
  }
  return affordances.map((item) => `
    <button data-affordance-id="${escapeHtml(item.id)}" title="${escapeHtml(item.description || item.label || "")}">
      ${escapeHtml(item.label || item.id)}
    </button>
  `).join("");
}

function bindObserverAffordanceActions(root, dossier) {
  root.querySelectorAll("[data-affordance-id]").forEach((button) => {
    button.addEventListener("click", () => act(() => applyObserverAffordance(dossier, button.dataset.affordanceId)));
  });
  root.querySelectorAll("[data-fallback-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.fallbackAction;
      if (action === "mediation") return act(sendSelectedMediation);
      if (action === "food") return act(() => addResourceAtSelectedLocation("food", 4));
      return act(sendObserverIntent);
    });
  });
}

function applyObserverAffordance(dossier, affordanceId) {
  const affordance = (dossier?.observer_affordances || []).find((item) => item.id === affordanceId);
  if (!affordance?.intervention) return sendObserverIntent();
  const actorId = observerActorId();
  const intervention = JSON.parse(JSON.stringify(affordance.intervention));
  intervention.actor_id = actorId;
  intervention.reason = `${actorId} 3D ${affordance.label || affordance.id}`;
  return api("/step", {
    method: "POST",
    body: JSON.stringify({
      days: 1,
      interventions: [intervention]
    })
  });
}

function selectedTargetIds() {
  if (document.getElementById("intentTarget").value !== "selected") return [];
  return selectedAgentId ? [selectedAgentId] : [];
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
  const input = document.getElementById("observerName");
  const name = (input?.value || "observer").trim() || "observer";
  localStorage.setItem("virtualSocietyObserverName", name);
  return name.replace(/[^a-zA-Z0-9 _-]/g, "").replace(/\\s+/g, "_") || "observer";
}

function sendObserverIntent() {
  const intent = document.getElementById("intent").value;
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
        reason: `${actorId} 3D intent ${intent}`,
        params
      }]
    })
  });
}

function sendSelectedMediation() {
  if (!selectedDossier?.agent) return sendObserverIntent();
  const crisis = (selectedDossier.relationship_links || []).find((item) => item.crisis);
  if (!crisis) return sendObserverIntent();
  const actorId = observerActorId();
  return api("/step", {
    method: "POST",
    body: JSON.stringify({
      days: 1,
      interventions: [{
        kind: "mediation",
        actor_id: actorId,
        reason: `${actorId} 3D mediated ${crisis.pair}`,
        params: {
          target_agent_ids: crisis.agent_ids,
          message: "Name the grievance and rebuild a practical agreement."
        }
      }]
    })
  });
}

function addResourceAtSelectedLocation(resource, amount) {
  const agent = selectedDossier?.agent;
  const actorId = observerActorId();
  return api("/step", {
    method: "POST",
    body: JSON.stringify({
      days: 1,
      interventions: [{
        kind: "resource",
        actor_id: actorId,
        reason: `${actorId} 3D supported ${agent?.name || "selected agent"}`,
        params: {
          resource,
          amount,
          location_id: agent?.location_id || "commons"
        }
      }]
    })
  });
}

document.getElementById("step1").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1 }) })));
document.getElementById("step7").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 7 }) })));
document.getElementById("step30").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 30 }) })));
document.getElementById("food").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "resource", actor_id: observerActorId(), reason: `${observerActorId()} 3D food aid`, params: { resource: "food", amount: 5 } }] }) })));
document.getElementById("hope").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "broadcast", actor_id: observerActorId(), reason: `${observerActorId()} 3D encouragement`, params: { tone: "hope", strength: 0.06, message: "Hold together." } }] }) })));
document.getElementById("storm").addEventListener("click", () => act(() => api("/step", { method: "POST", body: JSON.stringify({ days: 1, interventions: [{ kind: "disaster", actor_id: observerActorId(), reason: `${observerActorId()} 3D stress test`, params: { name: "storm", severity: 0.35 } }] }) })));
document.getElementById("reset").addEventListener("click", () => act(() => api("/reset", { method: "POST", body: JSON.stringify({ seed: latestFrame?.seed || 7 }) })));
document.getElementById("resetAlpha").addEventListener("click", () => act(() => api("/reset", { method: "POST", body: JSON.stringify({ seed: latestFrame?.seed || 7, world_preset: "generative_alpha" }) })));
document.getElementById("sendIntent").addEventListener("click", () => act(sendObserverIntent));
const savedObserverName = localStorage.getItem("virtualSocietyObserverName");
if (savedObserverName) document.getElementById("observerName").value = savedObserverName;
renderer.domElement.addEventListener("pointerdown", onPointerDown);
window.addEventListener("resize", resize);

resize();
refresh();
animate(0);
  </script>
</body>
</html>"""
