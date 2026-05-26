from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Action(str, Enum):
    FARM = "farm"
    GATHER = "gather"
    HAUL = "haul"
    REST = "rest"
    SOCIALIZE = "socialize"
    REPAIR = "repair"


@dataclass(frozen=True)
class Plan:
    action: Action
    priority: float
    reason: str
    target_id: str | None = None
    horizon_days: int = 1


@dataclass
class AgentProfile:
    background: str = ""
    values: list[str] = field(default_factory=list)
    long_term_goals: list[str] = field(default_factory=list)
    speech_style: str = "plain"


@dataclass
class MemoryItem:
    day: int
    kind: str
    text: str
    importance: float = 0.30
    tags: list[str] = field(default_factory=list)
    actor_id: str | None = None
    related_agent_ids: list[str] = field(default_factory=list)
    location_id: str | None = None


@dataclass
class LifeEpisode:
    day: int
    action: str
    location_id: str
    summary: str
    mood: str
    need_before: float
    need_after: float
    trust_before: float
    trust_after: float
    pressures: list[str] = field(default_factory=list)
    target_id: str | None = None


@dataclass
class Needs:
    food: float = 0.75
    energy: float = 0.75
    safety: float = 0.70
    belonging: float = 0.55
    meaning: float = 0.50

    def clamp(self) -> None:
        self.food = _clamp01(self.food)
        self.energy = _clamp01(self.energy)
        self.safety = _clamp01(self.safety)
        self.belonging = _clamp01(self.belonging)
        self.meaning = _clamp01(self.meaning)

    def average(self) -> float:
        return (self.food + self.energy + self.safety + self.belonging + self.meaning) / 5


@dataclass
class Agent:
    id: str
    name: str
    role: str
    location_id: str = "commons"
    profile: AgentProfile = field(default_factory=AgentProfile)
    needs: Needs = field(default_factory=Needs)
    skills: dict[str, float] = field(default_factory=dict)
    relationships: dict[str, float] = field(default_factory=dict)
    memories: list[str] = field(default_factory=list)
    memory_stream: list[MemoryItem] = field(default_factory=list)
    reflections: list[str] = field(default_factory=list)
    life_journal: list[LifeEpisode] = field(default_factory=list)
    active_plan: Plan | None = None
    plan_history: list[str] = field(default_factory=list)
    reputation: float = 0.50
    organization_ids: list[str] = field(default_factory=list)

    def choose_action(self, world: WorldState) -> Action:
        food_pressure = world.population * world.rules.food_per_agent * 1.15
        depot_food = sum(
            location.resources.get("food", 0.0)
            for location in world.locations
            if location.id in {"commons", "shelter_house"}
        )
        if world.resources.get("food", 0.0) > depot_food and depot_food < food_pressure:
            return Action.HAUL
        if self.needs.food < 0.42 or world.resources.get("food", 0.0) < food_pressure:
            return Action.FARM
        if self.needs.safety < 0.45 or world.resources.get("shelter", 0.0) < world.population * 0.75:
            return Action.REPAIR
        if self.needs.energy < 0.35:
            return Action.REST
        if self.needs.belonging < 0.46:
            return Action.SOCIALIZE
        return Action.GATHER


@dataclass(frozen=True)
class Event:
    day: int
    kind: str
    actor_id: str
    description: str
    effects: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Metrics:
    day: int
    population: int
    food: float
    materials: float
    shelter: float
    average_need: float
    average_trust: float
    average_reputation: float
    institutional_cohesion: float
    crisis_events: int


@dataclass
class Organization:
    id: str
    name: str
    kind: str
    home_location_id: str = "commons"
    members: list[str] = field(default_factory=list)
    norms: list[str] = field(default_factory=list)
    inventory_targets: dict[str, float] = field(default_factory=dict)
    exchange_preferences: dict[str, float] = field(default_factory=dict)
    cohesion: float = 0.55
    reputation: float = 0.50


@dataclass
class Location:
    id: str
    name: str
    kind: str
    condition: float = 0.60
    capacity: int = 12
    production: dict[str, float] = field(default_factory=dict)
    maintenance_need: float = 1.0
    resources: dict[str, float] = field(default_factory=lambda: {
        "food": 0.0,
        "materials": 0.0,
        "shelter": 0.0,
    })
    connected_location_ids: list[str] = field(default_factory=list)


@dataclass
class WorldRules:
    food_decay: float = 0.12
    energy_decay: float = 0.10
    belonging_decay: float = 0.025
    meaning_decay: float = 0.015
    shelter_safety_ratio: float = 0.70
    shelter_low_safety_decay: float = 0.04
    shelter_normal_safety_decay: float = 0.01
    shelter_safety_recovery: float = 0.012
    food_per_agent: float = 0.65
    exhaustion_work_threshold: float = 0.12
    haul_capacity: float = 3.2
    depot_food_target_days: float = 1.3
    workshop_material_target: float = 2.0
    route_base_energy_cost: float = 0.04
    route_hop_energy_cost: float = 0.018
    route_capacity_loss_per_hop: float = 0.12
    route_soft_capacity: float = 3.6
    route_congestion_wear: float = 0.0012
    farm_base_output: float = 1.35
    farm_skill_output: float = 1.65
    supply_route_base_capacity: float = 0.60
    supply_route_cohesion_capacity: float = 2.10
    cooperation_trust_gain: float = 0.0015
    scarcity_trust_loss: float = 0.001
    relationship_baseline: float = 0.55
    relationship_daily_drift: float = 0.0013
    relationship_crisis_threshold: float = 0.18
    relationship_repair_threshold: float = 0.42
    relationship_crisis_social_repair_bonus: float = 0.035
    observer_mediation_trust_gain: float = 0.08
    memory_limit: int = 30
    memory_stream_limit: int = 120
    life_journal_limit: int = 90
    reflection_limit: int = 20
    reflection_interval_days: int = 7
    plan_history_limit: int = 20
    reputation_baseline: float = 0.55
    reputation_daily_drift: float = 0.0030
    reputation_work_gain: float = 0.0024
    reputation_support_gain: float = 0.0022
    reputation_neglect_loss: float = 0.006
    organization_cohesion_baseline: float = 0.58
    organization_cohesion_daily_drift: float = 0.0020
    organization_cohesion_gain: float = 0.0024
    organization_cohesion_loss: float = 0.006
    institutional_belonging_gain: float = 0.015
    institutional_trust_repair_gain: float = 0.004
    location_work_wear: float = 0.0006
    location_maintenance_decay: float = 0.0009
    shelter_upkeep_per_agent: float = 0.007
    location_social_repair: float = 0.001
    location_repair_gain: float = 0.018
    location_natural_recovery: float = 0.003
    common_maintenance_threshold: float = 0.76
    common_maintenance_material_budget: float = 0.36
    common_maintenance_material_per_site: float = 0.14
    common_maintenance_condition_gain: float = 0.055
    organization_exchange_capacity: float = 0.72
    organization_exchange_min_cohesion: float = 0.48
    organization_exchange_surplus_buffer: float = 0.35
    organization_exchange_deficit_threshold: float = 0.22
    organization_exchange_cohesion_gain: float = 0.0009
    institutional_crisis_threshold: float = 0.35
    organization_fracture_threshold: float = 0.24
    organization_fracture_min_members: int = 4
    organization_fracture_cooldown_days: int = 28
    route_block_condition_threshold: float = 0.16
    route_block_excess_threshold: float = 2.5
    route_block_repair_need: float = 1.0
    route_repair_material_cost: float = 0.22
    route_repair_progress: float = 0.26


@dataclass
class WorldState:
    day: int = 0
    agents: list[Agent] = field(default_factory=list)
    resources: dict[str, float] = field(default_factory=lambda: {
        "food": 12.0,
        "materials": 8.0,
        "shelter": 4.0,
    })
    locations: list[Location] = field(default_factory=list)
    organizations: list[Organization] = field(default_factory=list)
    route_loads: dict[str, float] = field(default_factory=dict)
    blocked_routes: dict[str, float] = field(default_factory=dict)
    relationship_crises: dict[str, int] = field(default_factory=dict)
    organization_fractures: dict[str, int] = field(default_factory=dict)
    rules: WorldRules = field(default_factory=WorldRules)
    event_log: list[Event] = field(default_factory=list)

    @property
    def population(self) -> int:
        return len(self.agents)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
