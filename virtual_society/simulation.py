from __future__ import annotations

import random
from collections import deque
from collections.abc import Callable
from dataclasses import asdict
from typing import Iterable

from .cognition import CognitionProvider, RuleBasedCognition
from .dialogue import DialogueProvider, RuleBasedDialogue
from .generative_memory import CRITICAL_EVENT_KINDS, memory_from_event
from .interventions import Intervention, group_interventions
from .model import (
    Action,
    Agent,
    AgentProfile,
    Event,
    Location,
    MemoryItem,
    Metrics,
    Needs,
    Organization,
    Plan,
    WorldState,
)
from .reflection import ReflectionProvider, RuleBasedReflection


class Simulation:
    """Deterministic small-society simulator.

    The current model is intentionally small. Its job is to establish the
    core loop: state -> rules -> events -> metrics -> repeat.
    """

    def __init__(
        self,
        seed: int = 1,
        world: WorldState | None = None,
        cognition: CognitionProvider | None = None,
        reflection: ReflectionProvider | None = None,
        dialogue: DialogueProvider | None = None,
        world_preset: str = "base",
    ) -> None:
        self.seed = seed
        self.world_preset = world_preset
        self.rng = random.Random(seed)
        self.world = world if world is not None else self._create_world(world_preset)
        self.cognition = cognition if cognition is not None else RuleBasedCognition()
        self.reflection = reflection if reflection is not None else RuleBasedReflection()
        self.dialogue = dialogue if dialogue is not None else RuleBasedDialogue()
        self._sync_world_resources()

    def _create_world(self, world_preset: str) -> WorldState:
        if world_preset == "base":
            return self._create_initial_world()
        if world_preset == "generative_alpha":
            return self._create_generative_alpha_world()
        raise ValueError(f"Unknown world preset: {world_preset}")

    def run(
        self,
        days: int,
        interventions: Iterable[Intervention] = (),
        after_step: Callable[[WorldState, Metrics], None] | None = None,
    ) -> list[Metrics]:
        schedule = group_interventions(interventions)
        metrics: list[Metrics] = []
        for _ in range(days):
            next_day = self.world.day + 1
            metric = self.step(schedule.get(next_day, []))
            metrics.append(metric)
            if after_step is not None:
                after_step(self.world, metric)
        return metrics

    def step(self, interventions: Iterable[Intervention] = ()) -> Metrics:
        self.world.day += 1
        self.world.route_loads.clear()
        for intervention in interventions:
            self.apply_intervention(intervention)

        self._apply_daily_decay()
        self._apply_social_drift()
        self._apply_location_maintenance_pressure()
        self._apply_shelter_upkeep()
        self._apply_location_recovery()

        agents = list(self.world.agents)
        self.rng.shuffle(agents)
        actions_taken: list[tuple[Agent, Action]] = []
        for agent in agents:
            proposed_plan = self.cognition.propose_plan(agent, self.world)
            plan = self._validate_plan(agent, proposed_plan)
            self._record_plan(agent, proposed_plan, plan)
            self._apply_action(agent, plan)
            actions_taken.append((agent, plan.action))
            agent.needs.clamp()

        self._apply_cooperation_effects(actions_taken)
        self._apply_institutional_effects(actions_taken)
        self._apply_organization_exchange()
        self._apply_supply_routes()
        self._apply_route_repairs()
        self._apply_common_maintenance()
        self._apply_route_wear()
        self._consume_food()
        self._apply_social_pressure()
        self._apply_scarcity_pressure()
        self._apply_institutional_pressure()
        self._apply_relationship_crises()
        self._apply_organization_fractures()
        self._apply_reflections()
        return self.metrics()

    def metrics(self) -> Metrics:
        agents = self.world.agents
        average_need = sum(agent.needs.average() for agent in agents) / len(agents)
        average_reputation = sum(agent.reputation for agent in agents) / len(agents)
        trust_values = [
            trust
            for agent in agents
            for trust in agent.relationships.values()
        ]
        average_trust = sum(trust_values) / len(trust_values) if trust_values else 0.0
        organization_values = [organization.cohesion for organization in self.world.organizations]
        institutional_cohesion = (
            sum(organization_values) / len(organization_values)
            if organization_values
            else 0.0
        )
        crisis_events = sum(
            1
            for event in self.world.event_log
            if event.kind
            in {
                "hunger_crisis",
                "safety_crisis",
                "institutional_crisis",
                "organization_fracture",
                "relationship_crisis",
                "route_blocked",
            }
        )
        return Metrics(
            day=self.world.day,
            population=self.world.population,
            food=round(self.world.resources["food"], 2),
            materials=round(self.world.resources["materials"], 2),
            shelter=round(self.world.resources["shelter"], 2),
            average_need=round(average_need, 3),
            average_trust=round(average_trust, 3),
            average_reputation=round(average_reputation, 3),
            institutional_cohesion=round(institutional_cohesion, 3),
            crisis_events=crisis_events,
        )

    def apply_intervention(self, intervention: Intervention) -> None:
        if intervention.day != self.world.day:
            raise ValueError(
                f"Intervention for day {intervention.day} cannot be applied on day {self.world.day}"
            )

        if intervention.kind == "resource":
            resource = str(intervention.params["resource"])
            amount = float(intervention.params["amount"])
            self.inject_resource(
                resource=resource,
                amount=amount,
                reason=intervention.reason or "scheduled resource intervention",
                actor_id=intervention.actor_id,
                location_id=str(intervention.params.get("location_id", "commons")),
            )
            return

        if intervention.kind == "disaster":
            self._apply_disaster(intervention)
            return

        if intervention.kind == "edict":
            self._apply_edict(intervention)
            return

        if intervention.kind == "new_agent":
            self._apply_new_agent(intervention)
            return

        if intervention.kind == "broadcast":
            self._apply_broadcast(intervention)
            return

        if intervention.kind == "organization":
            self._apply_organization_intervention(intervention)
            return

        raise ValueError(f"Unknown intervention kind: {intervention.kind}")

    def inject_resource(
        self,
        resource: str,
        amount: float,
        reason: str = "external intervention",
        actor_id: str = "observer",
        location_id: str = "commons",
    ) -> None:
        before = self.world.resources.get(resource, 0.0)
        if amount >= 0:
            actual_change = self._add_location_resource(location_id, resource, amount)
        else:
            actual_change = -self._remove_location_resource(location_id, resource, -amount)
        self._sync_world_resources()
        self._record(
            kind="intervention",
            actor_id=actor_id,
            description=(
                f"{actor_id} changed {resource} at {location_id} "
                f"by {actual_change:.2f}: {reason}"
            ),
            effects={resource: self.world.resources.get(resource, 0.0) - before},
        )

    def snapshot(self) -> dict:
        return {
            "seed": self.seed,
            "world": asdict(self.world),
            "metrics": asdict(self.metrics()),
        }

    def _create_initial_world(self) -> WorldState:
        names = ["Ari", "Bo", "Chen", "Dina", "Eli", "Faye"]
        roles = ["farmer", "builder", "mediator", "forager", "caretaker", "maker"]
        role_locations = {
            "farmer": "north_field",
            "builder": "workshop",
            "mediator": "commons",
            "forager": "woodlot",
            "caretaker": "shelter_house",
            "maker": "workshop",
        }
        agents = [
            Agent(
                id=f"a{i + 1}",
                name=name,
                role=roles[i],
                location_id=role_locations[roles[i]],
                profile=_default_profile(name, roles[i]),
                needs=Needs(
                    food=self.rng.uniform(0.62, 0.88),
                    energy=self.rng.uniform(0.55, 0.90),
                    safety=self.rng.uniform(0.58, 0.85),
                    belonging=self.rng.uniform(0.42, 0.78),
                    meaning=self.rng.uniform(0.40, 0.72),
                ),
                skills={
                    "farming": self.rng.uniform(0.35, 0.85),
                    "building": self.rng.uniform(0.25, 0.80),
                    "social": self.rng.uniform(0.30, 0.88),
                },
            )
            for i, name in enumerate(names)
        ]

        for agent in agents:
            for other in agents:
                if agent.id != other.id:
                    agent.relationships[other.id] = self.rng.uniform(0.35, 0.70)

        organizations = [
            Organization(
                id="household_north",
                name="North Household",
                kind="household",
                home_location_id="north_field",
                members=["a1", "a2", "a3"],
                norms=["share_food", "care_for_members"],
                inventory_targets={"food": 2.4, "materials": 0.3, "shelter": 0.0},
                exchange_preferences={"food": 1.0, "materials": 0.4},
                cohesion=0.58,
            ),
            Organization(
                id="household_south",
                name="South Household",
                kind="household",
                home_location_id="shelter_house",
                members=["a4", "a5", "a6"],
                norms=["share_food", "care_for_members"],
                inventory_targets={"food": 2.2, "materials": 0.8, "shelter": 2.5},
                exchange_preferences={"food": 1.0, "materials": 0.8, "shelter": 0.5},
                cohesion=0.58,
            ),
            Organization(
                id="common_council",
                name="Common Council",
                kind="council",
                home_location_id="commons",
                members=[agent.id for agent in agents],
                norms=["work_contribution", "repair_common_shelter"],
                inventory_targets={"food": 3.2, "materials": 1.2, "shelter": 0.5},
                exchange_preferences={"food": 1.0, "materials": 1.0, "shelter": 0.3},
                cohesion=0.52,
            ),
            Organization(
                id="maker_guild",
                name="Maker Guild",
                kind="guild",
                home_location_id="workshop",
                members=["a2", "a6"],
                norms=["maintain_tools", "trade_materials"],
                inventory_targets={"food": 0.8, "materials": 2.2, "shelter": 0.5},
                exchange_preferences={"materials": 1.0, "shelter": 0.7, "food": 0.4},
                cohesion=0.54,
            ),
        ]
        for organization in organizations:
            for member_id in organization.members:
                member = _find_agent_in_list(agents, member_id)
                if member is not None and organization.id not in member.organization_ids:
                    member.organization_ids.append(organization.id)

        locations = [
            Location(
                id="commons",
                name="Commons",
                kind="civic",
                condition=0.66,
                capacity=18,
                production={"social": 1.15},
                maintenance_need=0.9,
                resources={"food": 3.0, "materials": 1.0, "shelter": 0.5},
                connected_location_ids=["north_field", "woodlot", "workshop", "shelter_house"],
            ),
            Location(
                id="north_field",
                name="North Field",
                kind="farm",
                condition=0.62,
                capacity=8,
                production={"food": 1.18},
                maintenance_need=1.15,
                resources={"food": 4.0, "materials": 0.5, "shelter": 0.0},
                connected_location_ids=["commons", "woodlot"],
            ),
            Location(
                id="woodlot",
                name="Woodlot",
                kind="wildland",
                condition=0.58,
                capacity=6,
                production={"food": 0.35, "materials": 1.22},
                maintenance_need=0.75,
                resources={"food": 1.0, "materials": 3.0, "shelter": 0.0},
                connected_location_ids=["commons", "north_field", "workshop"],
            ),
            Location(
                id="workshop",
                name="Workshop",
                kind="production",
                condition=0.60,
                capacity=8,
                production={"materials": 0.90, "shelter": 1.16},
                maintenance_need=1.25,
                resources={"food": 1.0, "materials": 3.5, "shelter": 0.5},
                connected_location_ids=["commons", "woodlot", "shelter_house"],
            ),
            Location(
                id="shelter_house",
                name="Shelter House",
                kind="dwelling",
                condition=0.64,
                capacity=10,
                production={"shelter": 1.0},
                maintenance_need=1.05,
                resources={"food": 3.0, "materials": 0.0, "shelter": 3.0},
                connected_location_ids=["commons", "workshop"],
            ),
        ]

        return WorldState(agents=agents, locations=locations, organizations=organizations)

    def _create_generative_alpha_world(self) -> WorldState:
        world = self._create_initial_world()
        world.rules.food_per_agent = 0.58
        world.rules.farm_base_output = 1.58
        world.rules.farm_skill_output = 1.85
        world.rules.haul_capacity = 4.2
        world.rules.depot_food_target_days = 1.45
        world.rules.supply_route_base_capacity = 0.80
        world.rules.supply_route_cohesion_capacity = 2.45
        world.rules.organization_exchange_capacity = 0.90
        world.rules.reputation_work_gain = 0.0024
        world.rules.reputation_support_gain = 0.0022
        world.rules.reputation_daily_drift = 0.0030
        world.rules.organization_cohesion_gain = 0.0024
        world.rules.organization_exchange_cohesion_gain = 0.0009
        world.rules.organization_cohesion_daily_drift = 0.0022
        world.rules.relationship_daily_drift = 0.0016
        world.rules.memory_stream_limit = 180

        world.locations.extend(
            [
                Location(
                    id="east_orchard",
                    name="East Orchard",
                    kind="farm",
                    condition=0.61,
                    capacity=7,
                    production={"food": 1.08, "social": 0.65},
                    maintenance_need=1.05,
                    resources={"food": 5.0, "materials": 0.8, "shelter": 0.0},
                    connected_location_ids=["commons", "north_field", "river_pier"],
                ),
                Location(
                    id="river_pier",
                    name="River Pier",
                    kind="logistics",
                    condition=0.59,
                    capacity=7,
                    production={"food": 0.42, "materials": 1.05},
                    maintenance_need=1.20,
                    resources={"food": 2.0, "materials": 3.0, "shelter": 0.2},
                    connected_location_ids=["commons", "woodlot", "east_orchard", "clinic"],
                ),
                Location(
                    id="clinic",
                    name="Clinic",
                    kind="care",
                    condition=0.63,
                    capacity=6,
                    production={"social": 1.10, "shelter": 0.55},
                    maintenance_need=1.10,
                    resources={"food": 1.5, "materials": 0.7, "shelter": 1.2},
                    connected_location_ids=["commons", "shelter_house", "river_pier"],
                ),
            ]
        )
        _add_connections(world, "commons", ["east_orchard", "river_pier", "clinic"])
        _add_connections(world, "north_field", ["east_orchard"])
        _add_connections(world, "woodlot", ["river_pier"])
        _add_connections(world, "shelter_house", ["clinic"])

        new_specs = [
            ("a7", "Gale", "scout", "east_orchard"),
            ("a8", "Hana", "cook", "shelter_house"),
            ("a9", "Ivo", "healer", "clinic"),
            ("a10", "Jules", "trader", "river_pier"),
            ("a11", "Kira", "organizer", "commons"),
            ("a12", "Lio", "apprentice", "workshop"),
        ]
        new_agents = [
            Agent(
                id=agent_id,
                name=name,
                role=role,
                location_id=location_id,
                profile=_default_profile(name, role),
                needs=Needs(
                    food=self.rng.uniform(0.60, 0.86),
                    energy=self.rng.uniform(0.55, 0.88),
                    safety=self.rng.uniform(0.56, 0.84),
                    belonging=self.rng.uniform(0.40, 0.76),
                    meaning=self.rng.uniform(0.42, 0.74),
                ),
                skills={
                    "farming": self.rng.uniform(0.30, 0.82),
                    "building": self.rng.uniform(0.26, 0.78),
                    "social": self.rng.uniform(0.34, 0.90),
                },
            )
            for agent_id, name, role, location_id in new_specs
        ]
        world.agents.extend(new_agents)
        _fill_relationships(world.agents, self.rng)

        common_council = self._find_organization_in_world(world, "common_council")
        if common_council is not None:
            common_council.members = [agent.id for agent in world.agents]
            common_council.inventory_targets = {"food": 6.6, "materials": 2.0, "shelter": 1.0}

        world.organizations.extend(
            [
                Organization(
                    id="household_east",
                    name="East Household",
                    kind="household",
                    home_location_id="east_orchard",
                    members=["a7", "a8", "a9"],
                    norms=["share_food", "warn_about_scarcity"],
                    inventory_targets={"food": 3.2, "materials": 0.7, "shelter": 0.4},
                    exchange_preferences={"food": 1.0, "materials": 0.6},
                    cohesion=0.56,
                ),
                Organization(
                    id="river_coop",
                    name="River Cooperative",
                    kind="cooperative",
                    home_location_id="river_pier",
                    members=["a10", "a11", "a12"],
                    norms=["maintain_routes", "honor_exchange"],
                    inventory_targets={"food": 1.6, "materials": 2.8, "shelter": 0.4},
                    exchange_preferences={"materials": 1.0, "food": 0.7, "shelter": 0.3},
                    cohesion=0.55,
                ),
                Organization(
                    id="care_circle",
                    name="Care Circle",
                    kind="care",
                    home_location_id="clinic",
                    members=["a5", "a8", "a9", "a11"],
                    norms=["protect_vulnerable", "share_warnings"],
                    inventory_targets={"food": 2.4, "materials": 1.0, "shelter": 1.4},
                    exchange_preferences={"food": 1.0, "shelter": 0.8, "materials": 0.5},
                    cohesion=0.57,
                ),
                Organization(
                    id="route_keepers",
                    name="Route Keepers",
                    kind="guild",
                    home_location_id="river_pier",
                    members=["a2", "a7", "a10", "a12"],
                    norms=["repair_routes", "keep_loads_visible"],
                    inventory_targets={"food": 1.2, "materials": 3.0, "shelter": 0.3},
                    exchange_preferences={"materials": 1.0, "food": 0.5},
                    cohesion=0.54,
                ),
            ]
        )
        self._assign_organization_memberships(world)
        return world

    def _find_organization_in_world(
        self,
        world: WorldState,
        organization_id: str,
    ) -> Organization | None:
        for organization in world.organizations:
            if organization.id == organization_id:
                return organization
        return None

    def _assign_organization_memberships(self, world: WorldState) -> None:
        for agent in world.agents:
            agent.organization_ids.clear()
        for organization in world.organizations:
            organization.members = list(dict.fromkeys(organization.members))
            for member_id in organization.members:
                member = _find_agent_in_list(world.agents, member_id)
                if member is not None and organization.id not in member.organization_ids:
                    member.organization_ids.append(organization.id)
            for first_id in organization.members:
                first = _find_agent_in_list(world.agents, first_id)
                if first is None:
                    continue
                for second_id in organization.members:
                    if first_id == second_id:
                        continue
                    first.relationships[second_id] = _clamp(
                        first.relationships.get(second_id, 0.50) + 0.035,
                        0.0,
                        1.0,
                    )

    def _apply_daily_decay(self) -> None:
        rules = self.world.rules
        for agent in self.world.agents:
            agent.needs.food -= rules.food_decay
            agent.needs.energy -= rules.energy_decay
            agent.needs.belonging -= rules.belonging_decay
            agent.needs.meaning -= rules.meaning_decay
            if self.world.resources["shelter"] < self.world.population * rules.shelter_safety_ratio:
                agent.needs.safety -= rules.shelter_low_safety_decay
            else:
                agent.needs.safety -= rules.shelter_normal_safety_decay
                agent.needs.safety += rules.shelter_safety_recovery
            agent.needs.clamp()

    def _apply_social_drift(self) -> None:
        rules = self.world.rules
        for agent in self.world.agents:
            for other_id, trust in list(agent.relationships.items()):
                if _relationship_key(agent.id, other_id) in self.world.relationship_crises:
                    continue
                drift = rules.relationship_daily_drift
                if self._share_organization(agent, other_id):
                    drift *= 0.55
                agent.relationships[other_id] = _clamp(
                    trust + (rules.relationship_baseline - trust) * drift,
                    0.0,
                    1.0,
                )
            agent.reputation = _clamp(
                agent.reputation + (rules.reputation_baseline - agent.reputation) * rules.reputation_daily_drift,
                0.0,
                1.0,
            )
        for organization in self.world.organizations:
            organization.cohesion = _clamp(
                organization.cohesion
                + (rules.organization_cohesion_baseline - organization.cohesion)
                * rules.organization_cohesion_daily_drift,
                0.0,
                1.0,
            )

    def _apply_location_recovery(self) -> None:
        recovery = self.world.rules.location_natural_recovery
        for location in self.world.locations:
            location.condition = _clamp(
                location.condition + recovery * (1.0 - location.condition),
                0.0,
                1.0,
            )

    def _apply_location_maintenance_pressure(self) -> None:
        rules = self.world.rules
        for location in self.world.locations:
            crowding = max(0, self._agents_at_location(location.id) - location.capacity)
            crowding_pressure = crowding / max(location.capacity, 1)
            decay = rules.location_maintenance_decay * location.maintenance_need * (
                1.0 + crowding_pressure
            )
            location.condition = _clamp(location.condition - decay, 0.0, 1.0)

    def _apply_shelter_upkeep(self) -> None:
        upkeep = self.world.population * self.world.rules.shelter_upkeep_per_agent
        if upkeep <= 0.0:
            return
        removed = self._remove_distributed_resource("shelter", upkeep)
        if removed > 0.0:
            self._sync_world_resources()

    def _validate_plan(self, agent: Agent, plan: Plan) -> Plan:
        if (
            plan.action == Action.REPAIR
            and self._location_resource("workshop", "materials") <= 0.05
            and self.world.resources["materials"] > 0.05
        ):
            return Plan(
                action=Action.HAUL,
                priority=plan.priority,
                reason="repair blocked by workshop material shortage; hauling materials first",
                horizon_days=plan.horizon_days,
            )

        if plan.action == Action.REPAIR and self.world.resources["materials"] <= 0.05:
            return Plan(
                action=Action.GATHER,
                priority=plan.priority,
                reason="repair blocked by lack of materials; gathering materials first",
                horizon_days=plan.horizon_days,
            )

        if (
            plan.action in {Action.FARM, Action.GATHER, Action.HAUL, Action.REPAIR}
            and agent.needs.energy <= self.world.rules.exhaustion_work_threshold
        ):
            return Plan(
                action=Action.REST,
                priority=plan.priority,
                reason="work plan blocked by exhaustion; resting first",
                horizon_days=plan.horizon_days,
            )

        if plan.action == Action.SOCIALIZE and plan.target_id is not None:
            if self._find_agent(plan.target_id) is None:
                return Plan(
                    action=Action.SOCIALIZE,
                    priority=plan.priority,
                    reason="social target unavailable; seeking connection broadly",
                    horizon_days=plan.horizon_days,
                )

        return plan

    def _record_plan(self, agent: Agent, proposed_plan: Plan, plan: Plan) -> None:
        previous = agent.active_plan
        agent.active_plan = plan
        agent.plan_history.append(
            f"day {self.world.day}: {plan.action.value} | {plan.reason}"
        )
        del agent.plan_history[:-self.world.rules.plan_history_limit]

        if proposed_plan.action != plan.action:
            self._record(
                "plan_blocked",
                agent.id,
                f"{agent.name}'s plan to {proposed_plan.action.value} was blocked; "
                f"now plans to {plan.action.value}.",
                {"priority": plan.priority},
                remember_actor=False,
            )

        if previous is None or previous.action != plan.action or previous.reason != plan.reason:
            self._record(
                "plan",
                agent.id,
                f"{agent.name} planned to {plan.action.value}: {plan.reason}",
                {"priority": plan.priority},
                remember_actor=False,
            )

    def _apply_action(self, agent: Agent, plan: Plan) -> None:
        action = plan.action
        self._move_for_action(agent, plan)
        if action == Action.FARM:
            location = self._find_location(agent.location_id)
            condition = location.condition if location is not None else 0.60
            rules = self.world.rules
            amount = (
                rules.farm_base_output
                + agent.skills["farming"] * rules.farm_skill_output
                + self.rng.uniform(-0.08, 0.12)
            ) * (0.82 + condition * 0.30) * self._location_production_factor(
                agent.location_id,
                "food",
            )
            self._add_location_resource(agent.location_id, "food", amount)
            self._sync_world_resources()
            agent.needs.energy -= 0.12
            agent.needs.meaning += 0.025
            self._wear_location(agent.location_id, self.world.rules.location_work_wear)
            self._record("work", agent.id, f"{agent.name} farmed food.", {"food": amount})
            return

        if action == Action.GATHER:
            location = self._find_location(agent.location_id)
            condition = location.condition if location is not None else 0.60
            amount = (
                0.45 + self.rng.uniform(0.0, 0.35)
            ) * (0.82 + condition * 0.25) * self._location_production_factor(
                agent.location_id,
                "materials",
            )
            self._add_location_resource(agent.location_id, "materials", amount)
            self._sync_world_resources()
            agent.needs.energy -= 0.08
            agent.needs.meaning += 0.015
            self._wear_location(agent.location_id, self.world.rules.location_work_wear)
            self._record("work", agent.id, f"{agent.name} gathered materials.", {"materials": amount})
            return

        if action == Action.HAUL:
            self._apply_haul_action(agent)
            return

        if action == Action.REST:
            agent.needs.energy += 0.32
            agent.needs.food -= 0.03
            self._repair_location(agent.location_id, self.world.rules.location_social_repair)
            self._record("rest", agent.id, f"{agent.name} rested.", {"energy": 0.32})
            return

        if action == Action.SOCIALIZE:
            partner = self._find_agent(plan.target_id) if plan.target_id is not None else None
            if partner is None or partner.id == agent.id:
                partner = self._pick_partner(agent)
            agent.needs.belonging += 0.18
            agent.needs.meaning += 0.03
            if partner is not None:
                pair_key = _relationship_key(agent.id, partner.id)
                repair_bonus = (
                    self.world.rules.relationship_crisis_social_repair_bonus
                    if pair_key in self.world.relationship_crises
                    else 0.0
                )
                agent.relationships[partner.id] = min(
                    1.0,
                    agent.relationships[partner.id] + 0.04 + repair_bonus,
                )
                partner.relationships[agent.id] = min(
                    1.0,
                    partner.relationships[agent.id] + 0.03 + repair_bonus,
                )
                partner.needs.belonging += 0.06
                partner.location_id = agent.location_id
                self._record("social", agent.id, f"{agent.name} strengthened ties with {partner.name}.", {})
                self._maybe_reconcile_relationship(agent, partner)
                baseline_dialogue = self._compose_social_dialogue(agent, partner)
                dialogue = self.dialogue.propose_dialogue(
                    agent,
                    partner,
                    self.world,
                    baseline_dialogue,
                )
                dialogue_event = self._record(
                    "dialogue",
                    agent.id,
                    dialogue.text,
                    {"trust": 0.035},
                    remember_actor=True,
                )
                self._remember(partner, dialogue_event)
            else:
                self._record("social", agent.id, f"{agent.name} sought connection.", {})
            self._repair_location(agent.location_id, self.world.rules.location_social_repair)
            return

        if action == Action.REPAIR:
            material_cost = self._remove_location_resource(agent.location_id, "materials", 0.45)
            shelter_gain = (
                material_cost
                * (0.75 + agent.skills["building"])
                * self._location_production_factor(agent.location_id, "shelter")
            )
            self._add_location_resource("shelter_house", "shelter", shelter_gain)
            self._sync_world_resources()
            agent.needs.energy -= 0.11
            agent.needs.safety += 0.04
            self._repair_location(agent.location_id, self.world.rules.location_repair_gain * material_cost)
            self._record(
                "work",
                agent.id,
                f"{agent.name} repaired shelter.",
                {"materials": -material_cost, "shelter": shelter_gain},
            )

    def _move_for_action(self, agent: Agent, plan: Plan) -> None:
        target_location = {
            Action.FARM: self._best_resource_location(agent, "food", "north_field"),
            Action.GATHER: self._best_resource_location(agent, "materials", "woodlot"),
            Action.HAUL: agent.location_id,
            Action.REPAIR: "workshop",
            Action.REST: "shelter_house",
            Action.SOCIALIZE: "commons",
        }[plan.action]
        if plan.action == Action.SOCIALIZE and plan.target_id is not None:
            partner = self._find_agent(plan.target_id)
            if partner is not None:
                target_location = partner.location_id
        if self._find_location(target_location) is not None:
            agent.location_id = target_location

    def _best_resource_location(self, agent: Agent, resource: str, fallback: str) -> str:
        candidates = [
            location
            for location in self.world.locations
            if location.production.get(resource, 0.0) > 0.0
        ]
        if not candidates:
            return fallback
        organization_home_ids = {
            organization.home_location_id
            for organization in self.world.organizations
            if organization.id in agent.organization_ids
        }

        def score(location: Location) -> float:
            production = location.production.get(resource, 0.0)
            crowding = self._agents_at_location(location.id) / max(location.capacity, 1)
            home_bonus = 0.18 if location.id in organization_home_ids else 0.0
            current_bonus = 0.08 if location.id == agent.location_id else 0.0
            return production * (0.78 + location.condition * 0.35) + home_bonus + current_bonus - crowding * 0.08

        return max(candidates, key=score).id

    def _apply_haul_action(self, agent: Agent) -> None:
        rules = self.world.rules
        commons_food = self._location_resource("commons", "food")
        shelter_food = self._location_resource("shelter_house", "food")
        depot_food = commons_food + shelter_food
        depot_target = self.world.population * rules.food_per_agent * rules.depot_food_target_days
        workshop_materials = self._location_resource("workshop", "materials")

        if depot_food < depot_target and self._remote_resource_total("food", {"commons", "shelter_house"}) > 0.05:
            destination_id = "commons"
            resource = "food"
            source = self._richest_reachable_location(
                resource,
                destination_id,
                exclude={"commons", "shelter_house"},
            )
        elif workshop_materials < rules.workshop_material_target and self._remote_resource_total("materials", {"workshop"}) > 0.05:
            destination_id = "workshop"
            resource = "materials"
            source = self._richest_reachable_location(
                resource,
                destination_id,
                exclude={"workshop"},
            )
        else:
            source = None
            destination_id = agent.location_id
            resource = "food"

        if source is None:
            agent.needs.energy += 0.04
            self._record("rest", agent.id, f"{agent.name} found no useful hauling route.", {"energy": 0.04})
            return

        distance = self._route_distance(source.id, destination_id)
        if distance is None:
            agent.needs.energy += 0.02
            self._record(
                "rest",
                agent.id,
                f"{agent.name} found no connected hauling route.",
                {"energy": 0.02},
            )
            return

        route_capacity = rules.haul_capacity * max(
            0.35,
            1.0 - rules.route_capacity_loss_per_hop * max(0, distance - 1),
        ) * self._route_condition_factor(source.id, destination_id)
        amount = min(route_capacity, source.resources.get(resource, 0.0))
        moved = self._move_location_resource(source.id, destination_id, resource, amount)
        self._register_route_use(source.id, destination_id, moved)
        agent.location_id = destination_id
        agent.needs.energy -= rules.route_base_energy_cost + distance * rules.route_hop_energy_cost
        agent.needs.meaning += 0.012
        self._sync_world_resources()
        self._record(
            "transport",
            agent.id,
            f"{agent.name} hauled {resource} from {source.name} to {self._location_name(destination_id)}.",
            {resource: moved, "route_distance": float(distance)},
        )

    def _apply_supply_routes(self) -> None:
        rules = self.world.rules
        depot_ids = {"commons", "shelter_house"}
        depot_food = sum(
            self._location_resource(location_id, "food")
            for location_id in depot_ids
        )
        required_food = self.world.population * rules.food_per_agent
        if depot_food >= required_food:
            return

        if not self.world.organizations:
            cohesion = 0.0
        else:
            cohesion = (
                sum(organization.cohesion for organization in self.world.organizations)
                / len(self.world.organizations)
            )
        capacity = (
            rules.supply_route_base_capacity
            + cohesion * rules.supply_route_cohesion_capacity
        )
        remaining_capacity = min(capacity, required_food - depot_food)
        moved_total = 0.0

        while remaining_capacity > 0.01:
            source = self._richest_reachable_location("food", "commons", exclude=depot_ids)
            if source is None:
                break
            distance = self._route_distance(source.id, "commons")
            if distance is None:
                break
            route_cost = max(1, distance)
            moved = self._move_location_resource(
                source.id,
                "commons",
                "food",
                remaining_capacity / route_cost,
            )
            if moved <= 0.0:
                break
            self._register_route_use(source.id, "commons", moved)
            moved_total += moved
            remaining_capacity -= moved * route_cost

        if moved_total <= 0.0:
            return

        self._sync_world_resources()
        self._record(
            "logistics",
            "common_council",
            "Common supply routes moved food into the shared depot.",
            {"food": moved_total},
            remember_actor=False,
        )

    def _apply_organization_exchange(self) -> None:
        rules = self.world.rules
        if self._average_institutional_cohesion() < rules.organization_exchange_min_cohesion:
            return

        exchanges = 0
        total_moved = 0.0
        resources = ["food", "materials", "shelter"]
        receivers = sorted(
            self.world.organizations,
            key=lambda organization: organization.cohesion,
            reverse=True,
        )

        for receiver in receivers:
            receiver_home = self._find_location(receiver.home_location_id)
            if receiver_home is None:
                continue
            for resource in resources:
                if resource == "food" and receiver_home.id not in {"commons", "shelter_house"}:
                    continue
                target = receiver.inventory_targets.get(resource)
                if target is None:
                    continue
                deficit = target - receiver_home.resources.get(resource, 0.0)
                if deficit <= rules.organization_exchange_deficit_threshold:
                    continue

                donor = self._find_exchange_donor(receiver, resource)
                if donor is None:
                    continue
                donor_home = self._find_location(donor.home_location_id)
                if donor_home is None:
                    continue

                distance = self._route_distance(donor_home.id, receiver_home.id)
                if distance is None:
                    continue
                donor_target = donor.inventory_targets.get(resource, 0.0)
                surplus = (
                    donor_home.resources.get(resource, 0.0)
                    - donor_target
                    - rules.organization_exchange_surplus_buffer
                )
                if surplus <= 0.0:
                    continue

                preference = receiver.exchange_preferences.get(resource, 1.0)
                route_capacity = (
                    rules.organization_exchange_capacity
                    * max(0.35, preference)
                    * self._route_condition_factor(donor_home.id, receiver_home.id)
                    / max(1, distance)
                )
                amount = min(deficit, surplus, route_capacity)
                moved = self._move_location_resource(
                    donor_home.id,
                    receiver_home.id,
                    resource,
                    amount,
                )
                if moved <= 0.0:
                    continue

                self._register_route_use(donor_home.id, receiver_home.id, moved)
                donor.cohesion = _clamp(
                    donor.cohesion + rules.organization_exchange_cohesion_gain * 0.5,
                    0.0,
                    1.0,
                )
                receiver.cohesion = _clamp(
                    receiver.cohesion + rules.organization_exchange_cohesion_gain,
                    0.0,
                    1.0,
                )
                donor.reputation = _clamp(donor.reputation + 0.002, 0.0, 1.0)
                self._sync_world_resources()
                self._record(
                    "exchange",
                    donor.id,
                    (
                        f"{donor.name} exchanged {resource} with {receiver.name} "
                        f"via {donor_home.name} -> {receiver_home.name}."
                    ),
                    {
                        resource: moved,
                        "route_distance": float(distance),
                    },
                    remember_actor=False,
                )
                exchanges += 1
                total_moved += moved
                break

        if exchanges <= 0:
            return

        self._record(
            "market",
            "common_council",
            f"Organizations completed {exchanges} exchange routes.",
            {"exchanges": float(exchanges), "resources": total_moved},
            remember_actor=False,
        )

    def _find_exchange_donor(
        self,
        receiver: Organization,
        resource: str,
    ) -> Organization | None:
        rules = self.world.rules
        receiver_home = self._find_location(receiver.home_location_id)
        if receiver_home is None:
            return None

        candidates: list[tuple[float, Organization]] = []
        for donor in self.world.organizations:
            if donor.id == receiver.id:
                continue
            donor_home = self._find_location(donor.home_location_id)
            if donor_home is None:
                continue
            if self._route_distance(donor_home.id, receiver_home.id) is None:
                continue
            surplus = (
                donor_home.resources.get(resource, 0.0)
                - donor.inventory_targets.get(resource, 0.0)
                - rules.organization_exchange_surplus_buffer
            )
            if surplus <= 0.0:
                continue
            preference = donor.exchange_preferences.get(resource, 0.5)
            candidates.append((surplus * max(0.1, preference) * donor.cohesion, donor))

        if not candidates:
            return None
        return max(candidates, key=lambda item: item[0])[1]

    def _apply_common_maintenance(self) -> None:
        rules = self.world.rules
        workshop_materials = self._location_resource("workshop", "materials")
        if workshop_materials <= 0.05:
            return

        cohesion = self._average_institutional_cohesion()
        if cohesion < 0.50:
            return

        budget = min(
            workshop_materials,
            rules.common_maintenance_material_budget * (0.50 + cohesion),
        )
        used_materials = 0.0
        repaired_condition = 0.0
        repaired_locations = 0
        candidates = sorted(
            (
                location
                for location in self.world.locations
                if location.condition < rules.common_maintenance_threshold
                and self._route_distance("workshop", location.id) is not None
            ),
            key=lambda location: (
                (rules.common_maintenance_threshold - location.condition)
                * location.maintenance_need
            ),
            reverse=True,
        )

        for location in candidates:
            if budget <= 0.01:
                break
            material_cost = min(budget, rules.common_maintenance_material_per_site)
            removed = self._remove_location_resource("workshop", "materials", material_cost)
            if removed <= 0.0:
                break
            gain = removed * rules.common_maintenance_condition_gain * (0.75 + cohesion)
            before = location.condition
            self._repair_location(location.id, gain)
            repaired_condition += location.condition - before
            used_materials += removed
            budget -= removed
            repaired_locations += 1
            self._register_route_use("workshop", location.id, removed)

        if used_materials <= 0.0:
            return

        self._sync_world_resources()
        self._record(
            "maintenance",
            "common_council",
            f"Common maintenance repaired {repaired_locations} locations.",
            {
                "materials": -used_materials,
                "condition": repaired_condition,
                "locations": float(repaired_locations),
            },
            remember_actor=False,
        )

    def _apply_route_wear(self) -> None:
        rules = self.world.rules
        total_excess = 0.0
        affected_routes = 0
        newly_blocked: list[str] = []
        for route_key, load in list(self.world.route_loads.items()):
            soft_capacity = rules.route_soft_capacity * self._edge_condition_factor(route_key)
            if load <= soft_capacity:
                continue
            excess = load - soft_capacity
            wear = min(0.012, excess * rules.route_congestion_wear)
            for location_id in route_key.split("|"):
                self._wear_location(location_id, wear)
            if self._should_block_route(route_key, excess):
                self.world.blocked_routes[route_key] = max(
                    self.world.blocked_routes.get(route_key, 0.0),
                    rules.route_block_repair_need,
                )
                newly_blocked.append(route_key)
            total_excess += excess
            affected_routes += 1

        if total_excess <= 0.0:
            return

        self._record(
            "route_strain",
            "common_council",
            f"{affected_routes} routes were strained by heavy traffic.",
            {"route_excess": total_excess, "routes": float(affected_routes)},
            remember_actor=False,
        )
        for route_key in newly_blocked:
            self._record(
                "route_blocked",
                "common_council",
                f"Route {route_key} became blocked after repeated strain and poor condition.",
                {"repair_need": self.world.blocked_routes[route_key]},
                remember_all=True,
            )

    def _should_block_route(self, route_key: str, excess: float) -> bool:
        if route_key in self.world.blocked_routes:
            return False
        if excess < self.world.rules.route_block_excess_threshold:
            return False
        location_ids = route_key.split("|")
        conditions = [
            location.condition
            for location_id in location_ids
            if (location := self._find_location(location_id)) is not None
        ]
        if not conditions:
            return False
        return min(conditions) <= self.world.rules.route_block_condition_threshold

    def _apply_route_repairs(self) -> None:
        if not self.world.blocked_routes:
            return
        rules = self.world.rules
        workshop_materials = self._location_resource("workshop", "materials")
        if workshop_materials <= 0.05:
            return

        cohesion = self._average_institutional_cohesion()
        if cohesion < 0.45:
            return

        repaired_routes = 0
        used_materials = 0.0
        for route_key, repair_need in sorted(list(self.world.blocked_routes.items())):
            if workshop_materials <= 0.05:
                break
            material_cost = min(workshop_materials, rules.route_repair_material_cost)
            removed = self._remove_location_resource("workshop", "materials", material_cost)
            if removed <= 0.0:
                break
            workshop_materials -= removed
            used_materials += removed
            remaining = round(
                repair_need - rules.route_repair_progress * (0.65 + cohesion),
                3,
            )
            if remaining <= 0.0:
                del self.world.blocked_routes[route_key]
                repaired_routes += 1
                self._record(
                    "route_reopened",
                    "common_council",
                    f"Route {route_key} reopened after common repair work.",
                    {"materials": -removed},
                    remember_all=True,
                )
            else:
                self.world.blocked_routes[route_key] = remaining

        if used_materials <= 0.0:
            return

        self._sync_world_resources()
        if repaired_routes <= 0:
            self._record(
                "route_repair",
                "common_council",
                "Common repair crews reduced blocked route repair backlog.",
                {"materials": -used_materials},
                remember_actor=False,
            )

    def _consume_food(self) -> None:
        food_per_agent = self.world.rules.food_per_agent
        population = max(self.world.population, 1)
        required_food = population * food_per_agent
        available_food = (
            self._location_resource("commons", "food")
            + self._location_resource("shelter_house", "food")
        )

        if available_food >= required_food:
            removed_from_commons = self._remove_location_resource("commons", "food", required_food)
            remaining = required_food - removed_from_commons
            if remaining > 0:
                self._remove_location_resource("shelter_house", "food", remaining)
            self._sync_world_resources()
            for agent in self.world.agents:
                agent.needs.food += 0.22
                agent.needs.clamp()
            return

        nutrition_ratio = _clamp(available_food / required_food, 0.0, 1.0)
        self._remove_location_resource("commons", "food", self._location_resource("commons", "food"))
        self._remove_location_resource("shelter_house", "food", self._location_resource("shelter_house", "food"))
        self._sync_world_resources()
        food_delta = 0.22 * nutrition_ratio - 0.22 * (1.0 - nutrition_ratio)
        for agent in self.world.agents:
            agent.needs.food += food_delta
            agent.needs.clamp()

        if nutrition_ratio < 0.55:
            self._record(
                "hunger_crisis",
                "society",
                "Food rationing failed to meet basic nutrition.",
                {"nutrition": nutrition_ratio, "food_need": food_delta},
                remember_all=True,
            )
        else:
            self._record(
                "rationing",
                "society",
                "Food was rationed across the society.",
                {"nutrition": nutrition_ratio, "food_need": food_delta},
                remember_all=True,
            )

    def _apply_cooperation_effects(self, actions_taken: list[tuple[Agent, Action]]) -> None:
        cooperative_actions = {Action.FARM, Action.GATHER, Action.HAUL, Action.REPAIR}
        by_action: dict[Action, list[Agent]] = {}
        for agent, action in actions_taken:
            if action in cooperative_actions:
                by_action.setdefault(action, []).append(agent)

        for action, agents in by_action.items():
            if len(agents) < 2:
                continue
            gain = self.world.rules.cooperation_trust_gain
            for agent in agents:
                agent.needs.belonging += gain
                for other in agents:
                    if other.id == agent.id:
                        continue
                    agent.relationships[other.id] = min(
                        1.0,
                        agent.relationships.get(other.id, 0.5) + gain,
                    )
                agent.needs.clamp()
            self._record(
                "cooperation",
                "society",
                f"{len(agents)} agents coordinated on {action.value}.",
                {"trust": gain},
            )

    def _apply_institutional_effects(self, actions_taken: list[tuple[Agent, Action]]) -> None:
        rules = self.world.rules
        productive_actions = {Action.FARM, Action.GATHER, Action.HAUL, Action.REPAIR}
        supportive_actions = {Action.SOCIALIZE}
        actions_by_id = {agent.id: action for agent, action in actions_taken}

        for agent, action in actions_taken:
            if action in productive_actions:
                agent.reputation = _clamp(
                    agent.reputation + rules.reputation_work_gain,
                    0.0,
                    1.0,
                )
            elif action in supportive_actions:
                agent.reputation = _clamp(
                    agent.reputation + rules.reputation_support_gain,
                    0.0,
                    1.0,
                )

        average_need = (
            sum(agent.needs.average() for agent in self.world.agents)
            / max(self.world.population, 1)
        )
        food_floor = self.world.population * rules.food_per_agent * 0.40
        shared_pressure = average_need < 0.43 or self.world.resources["food"] < food_floor
        neglect_count = 0
        if shared_pressure:
            for agent, action in actions_taken:
                if action == Action.REST and agent.needs.energy > 0.70:
                    agent.reputation = _clamp(
                        agent.reputation - rules.reputation_neglect_loss,
                        0.0,
                        1.0,
                    )
                    neglect_count += 1
            if neglect_count:
                self._record(
                    "norm_warning",
                    "society",
                    f"{neglect_count} agents rested while shared pressure was high.",
                    {"reputation": -rules.reputation_neglect_loss * neglect_count},
                    remember_actor=False,
                )

        for organization in self.world.organizations:
            members = [
                agent
                for member_id in organization.members
                if (agent := self._find_agent(member_id)) is not None
            ]
            if not members:
                continue
            member_actions = [
                actions_by_id[agent.id]
                for agent in members
                if agent.id in actions_by_id
            ]
            if not member_actions:
                continue

            contribution_count = sum(
                1
                for action in member_actions
                if action in productive_actions or action in supportive_actions
            )
            contribution_share = contribution_count / len(member_actions)
            if contribution_share >= 0.50:
                organization.cohesion = _clamp(
                    organization.cohesion
                    + rules.organization_cohesion_gain * contribution_share,
                    0.0,
                    1.0,
                )
            elif shared_pressure:
                organization.cohesion = _clamp(
                    organization.cohesion
                    - rules.organization_cohesion_loss * (1.0 - contribution_share),
                    0.0,
                    1.0,
                )

            organization.reputation = round(
                sum(agent.reputation for agent in members) / len(members),
                3,
            )

        for agent in self.world.agents:
            cohesion_values = [
                organization.cohesion
                for organization in self.world.organizations
                if organization.id in agent.organization_ids
            ]
            if not cohesion_values:
                continue
            average_cohesion = sum(cohesion_values) / len(cohesion_values)
            if average_cohesion <= 0.55:
                continue
            gain = rules.institutional_belonging_gain * average_cohesion
            agent.needs.belonging += gain
            agent.needs.meaning += gain * 0.50
            trust_gain = rules.institutional_trust_repair_gain * average_cohesion
            for other_id, trust in list(agent.relationships.items()):
                if self._share_organization(agent, other_id):
                    agent.relationships[other_id] = _clamp(
                        trust + trust_gain * (1.0 - trust),
                        0.0,
                        1.0,
                    )
            agent.needs.clamp()

    def _apply_social_pressure(self) -> None:
        average_need = sum(agent.needs.average() for agent in self.world.agents) / self.world.population
        if average_need >= 0.38:
            return

        for agent in self.world.agents:
            agent.needs.safety -= 0.03
            agent.needs.belonging -= 0.04
            for other_id, trust in list(agent.relationships.items()):
                agent.relationships[other_id] = max(0.0, trust - 0.02)
            agent.needs.clamp()

        self._record(
            "safety_crisis",
            "society",
            "Low shared wellbeing weakened safety and trust.",
            {"average_need": average_need},
        )

    def _apply_scarcity_pressure(self) -> None:
        food_floor = self.world.population * self.world.rules.food_per_agent * 0.25
        if self.world.resources["food"] >= food_floor:
            return

        loss = self.world.rules.scarcity_trust_loss
        for agent in self.world.agents:
            agent.needs.safety -= loss
            for other_id, trust in list(agent.relationships.items()):
                agent.relationships[other_id] = max(0.0, trust - loss)
            agent.needs.clamp()

        self._record(
            "scarcity_pressure",
            "society",
            "Food scarcity slightly weakened safety and trust.",
            {"trust": -loss},
        )

    def _apply_institutional_pressure(self) -> None:
        if not self.world.organizations:
            return

        cohesion = (
            sum(organization.cohesion for organization in self.world.organizations)
            / len(self.world.organizations)
        )
        threshold = self.world.rules.institutional_crisis_threshold
        if cohesion >= threshold:
            return

        loss = min(0.05, (threshold - cohesion) * 0.18)
        for agent in self.world.agents:
            agent.needs.belonging -= loss
            agent.needs.meaning -= loss * 0.75
            for other_id, trust in list(agent.relationships.items()):
                agent.relationships[other_id] = max(0.0, trust - loss * 0.35)
            agent.needs.clamp()

        self._record(
            "institutional_crisis",
            "society",
            "Weak institutional cohesion reduced belonging, meaning, and trust.",
            {"institutional_cohesion": -loss},
        )

    def _apply_relationship_crises(self) -> None:
        rules = self.world.rules
        candidates: list[tuple[float, Agent, Agent]] = []
        for index, agent in enumerate(self.world.agents):
            for other in self.world.agents[index + 1:]:
                pair_key = _relationship_key(agent.id, other.id)
                if pair_key in self.world.relationship_crises:
                    continue
                trust = (
                    agent.relationships.get(other.id, 0.50)
                    + other.relationships.get(agent.id, 0.50)
                ) / 2
                if trust <= rules.relationship_crisis_threshold:
                    candidates.append((trust, agent, other))

        for trust, agent, other in sorted(candidates, key=lambda item: item[0])[:3]:
            pair_key = _relationship_key(agent.id, other.id)
            self.world.relationship_crises[pair_key] = self.world.day
            self._record(
                "relationship_crisis",
                "society",
                (
                    f"{agent.name} and {other.name} entered a relationship crisis; "
                    f"trust fell to {trust:.3f}."
                ),
                {"trust": -round(rules.relationship_crisis_threshold - trust, 3)},
                remember_all=True,
            )

    def _maybe_reconcile_relationship(self, agent: Agent, partner: Agent) -> None:
        pair_key = _relationship_key(agent.id, partner.id)
        if pair_key not in self.world.relationship_crises:
            return
        trust = (
            agent.relationships.get(partner.id, 0.50)
            + partner.relationships.get(agent.id, 0.50)
        ) / 2
        if trust < self.world.rules.relationship_repair_threshold:
            return

        started_day = self.world.relationship_crises.pop(pair_key)
        self._record(
            "reconciliation",
            agent.id,
            (
                f"{agent.name} and {partner.name} reconciled after a relationship "
                f"crisis that began on day {started_day}."
            ),
            {"trust": trust},
            remember_all=True,
        )

    def _apply_organization_fractures(self) -> None:
        rules = self.world.rules
        for organization in list(self.world.organizations):
            if len(organization.members) < rules.organization_fracture_min_members:
                continue
            if organization.cohesion > rules.organization_fracture_threshold:
                continue
            last_fracture_day = self.world.organization_fractures.get(organization.id)
            if (
                last_fracture_day is not None
                and self.world.day - last_fracture_day < rules.organization_fracture_cooldown_days
            ):
                continue
            members = [
                agent
                for member_id in organization.members
                if (agent := self._find_agent(member_id)) is not None
            ]
            if len(members) < rules.organization_fracture_min_members:
                continue

            scored_members = sorted(
                (
                    (self._average_peer_trust(agent, organization), agent)
                    for agent in members
                ),
                key=lambda item: (item[0], item[1].id),
            )
            split_count = min(max(2, len(members) // 3), len(members) - 2)
            breakaway_agents = [agent for _, agent in scored_members[:split_count]]
            if len(breakaway_agents) < 2:
                continue

            self._create_splinter_organization(organization, breakaway_agents)
            return

    def _average_peer_trust(self, agent: Agent, organization: Organization) -> float:
        peer_ids = [member_id for member_id in organization.members if member_id != agent.id]
        if not peer_ids:
            return 0.0
        return sum(agent.relationships.get(peer_id, 0.50) for peer_id in peer_ids) / len(peer_ids)

    def _create_splinter_organization(
        self,
        organization: Organization,
        breakaway_agents: list[Agent],
    ) -> None:
        breakaway_ids = [agent.id for agent in breakaway_agents]
        breakaway_names = ", ".join(agent.name for agent in breakaway_agents)
        organization.members = [
            member_id
            for member_id in organization.members
            if member_id not in breakaway_ids
        ]
        for agent in breakaway_agents:
            if organization.id in agent.organization_ids:
                agent.organization_ids.remove(organization.id)

        organization.cohesion = _clamp(organization.cohesion - 0.04, 0.0, 1.0)
        new_id = self._unique_organization_id(f"{organization.id}_splinter")
        home_location_id = breakaway_agents[0].location_id
        splinter = Organization(
            id=new_id,
            name=f"{organization.name} Splinter",
            kind=f"{organization.kind}_splinter",
            home_location_id=home_location_id,
            members=breakaway_ids,
            norms=list(dict.fromkeys([*organization.norms[:2], "repair_trust"])),
            inventory_targets=dict(organization.inventory_targets),
            exchange_preferences=dict(organization.exchange_preferences),
            cohesion=0.38,
            reputation=round(
                sum(agent.reputation for agent in breakaway_agents) / len(breakaway_agents),
                3,
            ),
        )
        self.world.organizations.append(splinter)
        for agent in breakaway_agents:
            if splinter.id not in agent.organization_ids:
                agent.organization_ids.append(splinter.id)

        self.world.organization_fractures[organization.id] = self.world.day
        self._record(
            "organization_fracture",
            organization.id,
            (
                f"{organization.name} fractured; {breakaway_names} formed "
                f"{splinter.name} at {self._location_name(home_location_id)}."
            ),
            {
                "members": -float(len(breakaway_ids)),
                "cohesion": organization.cohesion,
            },
            remember_all=True,
        )

    def _unique_organization_id(self, base_id: str) -> str:
        candidate = base_id
        index = 2
        while self._find_organization(candidate) is not None:
            candidate = f"{base_id}_{index}"
            index += 1
        return candidate

    def _apply_disaster(self, intervention: Intervention) -> None:
        name = str(intervention.params.get("name", "disaster"))
        severity = _clamp(float(intervention.params.get("severity", 0.3)), 0.0, 1.0)
        food_loss = min(self.world.resources["food"], self.world.population * severity * 0.9)
        materials_loss = min(self.world.resources["materials"], self.world.population * severity * 0.65)
        shelter_loss = min(self.world.resources["shelter"], self.world.population * severity * 0.25)

        food_loss = self._remove_distributed_resource("food", food_loss)
        materials_loss = self._remove_distributed_resource("materials", materials_loss)
        shelter_loss = self._remove_distributed_resource("shelter", shelter_loss)
        self._sync_world_resources()

        for agent in self.world.agents:
            agent.needs.safety -= 0.16 * severity
            agent.needs.energy -= 0.06 * severity
            agent.needs.clamp()

        self._record(
            "disaster",
            intervention.actor_id,
            f"{name} damaged the society: {intervention.reason or 'external shock'}.",
            {
                "food": -food_loss,
                "materials": -materials_loss,
                "shelter": -shelter_loss,
                "severity": severity,
            },
            remember_all=True,
        )

    def _apply_edict(self, intervention: Intervention) -> None:
        rule = str(intervention.params["rule"])
        value = float(intervention.params["value"])
        if not hasattr(self.world.rules, rule):
            raise ValueError(f"Unknown rule: {rule}")
        old_value = float(getattr(self.world.rules, rule))
        setattr(self.world.rules, rule, value)
        self._record(
            "edict",
            intervention.actor_id,
            f"{intervention.actor_id} changed rule {rule} from {old_value:.3f} to {value:.3f}.",
            {rule: value - old_value},
        )

    def _apply_new_agent(self, intervention: Intervention) -> None:
        agent_id = str(intervention.params.get("id") or self._next_agent_id())
        if any(agent.id == agent_id for agent in self.world.agents):
            raise ValueError(f"Agent already exists: {agent_id}")

        name = str(intervention.params.get("name", agent_id))
        role = str(intervention.params.get("role", "newcomer"))
        skills = {
            "farming": float(intervention.params.get("farming", self.rng.uniform(0.30, 0.75))),
            "building": float(intervention.params.get("building", self.rng.uniform(0.25, 0.70))),
            "social": float(intervention.params.get("social", self.rng.uniform(0.30, 0.78))),
        }
        agent = Agent(
            id=agent_id,
            name=name,
            role=role,
            location_id=str(intervention.params.get("location_id", "commons")),
            profile=_default_profile(name, role),
            needs=Needs(
                food=float(intervention.params.get("food_need", 0.68)),
                energy=float(intervention.params.get("energy_need", 0.68)),
                safety=float(intervention.params.get("safety_need", 0.62)),
                belonging=float(intervention.params.get("belonging_need", 0.40)),
                meaning=float(intervention.params.get("meaning_need", 0.45)),
            ),
            skills=skills,
        )
        agent.needs.clamp()
        if self._find_location(agent.location_id) is None:
            raise ValueError(f"Unknown location: {agent.location_id}")

        default_trust = float(intervention.params.get("initial_trust", 0.45))
        for other in self.world.agents:
            trust = _clamp(default_trust + self.rng.uniform(-0.07, 0.07), 0.0, 1.0)
            agent.relationships[other.id] = trust
            other.relationships[agent.id] = trust

        organization_ids = _string_list(intervention.params.get("organization_ids"))
        if not organization_ids and self._find_organization("common_council") is not None:
            organization_ids = ["common_council"]
        for organization_id in organization_ids:
            organization = self._find_organization(organization_id)
            if organization is None:
                raise ValueError(f"Unknown organization: {organization_id}")
            if agent.id not in organization.members:
                organization.members.append(agent.id)
            if organization.id not in agent.organization_ids:
                agent.organization_ids.append(organization.id)

        self.world.agents.append(agent)
        self._record(
            "arrival",
            intervention.actor_id,
            f"{name} joined the society as {role}.",
            {"population": 1.0},
            remember_all=True,
        )

    def _apply_organization_intervention(self, intervention: Intervention) -> None:
        organization_id = str(
            intervention.params.get("id")
            or f"org_{len(self.world.organizations) + 1}"
        )
        if self._find_organization(organization_id) is not None:
            raise ValueError(f"Organization already exists: {organization_id}")

        members = _string_list(intervention.params.get("members"))
        if not members:
            members = [agent.id for agent in self.world.agents]
        missing_members = [
            member_id
            for member_id in members
            if self._find_agent(member_id) is None
        ]
        if missing_members:
            raise ValueError(f"Unknown organization members: {', '.join(missing_members)}")

        organization = Organization(
            id=organization_id,
            name=str(intervention.params.get("name", organization_id)),
            kind=str(intervention.params.get("kind", "association")),
            home_location_id=str(intervention.params.get("home_location_id", "commons")),
            members=list(dict.fromkeys(members)),
            norms=_string_list(intervention.params.get("norms")),
            inventory_targets=_float_dict(intervention.params.get("inventory_targets")),
            exchange_preferences=_float_dict(intervention.params.get("exchange_preferences")),
            cohesion=_clamp(float(intervention.params.get("cohesion", 0.55)), 0.0, 1.0),
            reputation=_clamp(float(intervention.params.get("reputation", 0.50)), 0.0, 1.0),
        )
        if self._find_location(organization.home_location_id) is None:
            raise ValueError(f"Unknown organization home location: {organization.home_location_id}")
        self.world.organizations.append(organization)
        for member_id in organization.members:
            member = self._find_agent(member_id)
            if member is not None and organization.id not in member.organization_ids:
                member.organization_ids.append(organization.id)

        self._record(
            "organization",
            intervention.actor_id,
            f"{organization.name} formed as a {organization.kind}.",
            {"members": float(len(organization.members)), "cohesion": organization.cohesion},
            remember_all=True,
        )

    def _apply_broadcast(self, intervention: Intervention) -> None:
        message = str(intervention.params.get("message", ""))
        tone = str(intervention.params.get("tone", "neutral"))
        strength = _clamp(float(intervention.params.get("strength", 0.05)), 0.0, 0.25)
        intent = _normalized_intent(intervention.params.get("intent"))
        recipients = self._broadcast_recipients(intervention)

        if tone == "hope":
            for agent in recipients:
                agent.needs.meaning += strength
                agent.needs.belonging += strength * 0.5
                agent.needs.clamp()
        elif tone == "fear":
            for agent in recipients:
                agent.needs.safety -= strength
                agent.needs.meaning -= strength * 0.4
                agent.needs.clamp()
        else:
            for agent in recipients:
                agent.needs.meaning += strength * 0.25
                agent.needs.clamp()

        if intent == "repair_routes":
            for agent in recipients:
                agent.needs.meaning += strength * 0.35
                agent.needs.safety += strength * 0.15
                agent.needs.clamp()
        elif intent == "reconcile_relationships":
            for agent in recipients:
                agent.needs.belonging += strength * 0.6
                agent.needs.meaning += strength * 0.2
                agent.needs.clamp()
        elif intent == "protect_food":
            for agent in recipients:
                agent.needs.safety += strength * 0.1
                agent.needs.meaning += strength * 0.25
                agent.needs.clamp()

        effects = {
            "strength": strength,
            "target_count": float(len(recipients)),
        }
        if intent:
            effects[f"intent_{intent}"] = strength
        target_text = _broadcast_target_text(recipients, self.world.agents)
        intent_text = f" intent {intent}" if intent else ""
        event = self._record(
            "broadcast",
            intervention.actor_id,
            f"{intervention.actor_id} broadcast{intent_text} {tone} message to {target_text}: {message}",
            effects,
            remember_actor=False,
        )
        for agent in recipients:
            self._remember(agent, event)

    def _broadcast_recipients(self, intervention: Intervention) -> list[Agent]:
        target_ids = set(_string_list(intervention.params.get("target_agent_ids")))
        if not target_ids:
            return list(self.world.agents)
        return [agent for agent in self.world.agents if agent.id in target_ids]

    def _apply_reflections(self) -> None:
        interval = self.world.rules.reflection_interval_days
        if interval < 1 or self.world.day % interval != 0:
            return
        for agent in self.world.agents:
            proposal = self.reflection.propose_reflection(
                agent,
                self.world,
                self.world.day,
                interval,
            )
            summary = proposal.summary
            agent.reflections.append(f"day {self.world.day}: {summary}")
            del agent.reflections[:-self.world.rules.reflection_limit]
            self._record(
                "reflection",
                agent.id,
                summary,
                {"importance": 0.76},
                remember_actor=True,
            )

    def _compose_social_dialogue(self, agent: Agent, partner: Agent) -> str:
        shared_orgs = sorted(set(agent.organization_ids) & set(partner.organization_ids))
        shared_goal = (
            agent.profile.long_term_goals[0]
            if agent.profile.long_term_goals
            else "stay useful"
        )
        partner_value = partner.profile.values[0] if partner.profile.values else "stability"
        salient_memory = self._salient_dialogue_memory(agent, partner)
        trust = (
            agent.relationships.get(partner.id, 0.50)
            + partner.relationships.get(agent.id, 0.50)
        ) / 2
        relation = "with fragile trust"
        if trust >= 0.66:
            relation = "as trusted partners"
        elif trust >= 0.52:
            relation = "with workable trust"

        evidence = ""
        if salient_memory is not None:
            evidence = (
                f" They grounded the talk in day {salient_memory.day}: "
                f"{salient_memory.text.rstrip('.')}."
            )
        if shared_orgs:
            return (
                f"{agent.name} and {partner.name} discussed {shared_orgs[0]} "
                f"{relation}.{evidence} {agent.name} connected it to {shared_goal}; "
                f"{partner.name} weighed it against {partner_value}."
            )
        return (
            f"{agent.name} asked {partner.name} what the settlement needs next "
            f"{relation}.{evidence} {partner.name} answered from a concern "
            f"for {partner_value}."
        )

    def _salient_dialogue_memory(self, agent: Agent, partner: Agent) -> MemoryItem | None:
        candidates = [
            memory
            for memory in [*agent.memory_stream[-14:], *partner.memory_stream[-14:]]
            if self.world.day - memory.day <= 21
        ]
        if not candidates:
            return None

        routine_kinds = {"dialogue", "plan", "rest", "social"}
        preferred = [
            memory
            for memory in candidates
            if memory.kind not in routine_kinds or memory.importance >= 0.75
        ]
        search_space = preferred or candidates
        scored = [
            (
                1 if memory.kind in CRITICAL_EVENT_KINDS else 0,
                memory.importance,
                memory.day,
                -index,
                memory,
            )
            for index, memory in enumerate(search_space)
        ]
        return max(scored, key=lambda item: item[:4])[-1]

    def _pick_partner(self, agent: Agent) -> Agent | None:
        candidates = [other for other in self.world.agents if other.id != agent.id]
        if not candidates:
            return None
        return max(candidates, key=lambda other: agent.relationships.get(other.id, 0.0))

    def _next_agent_id(self) -> str:
        numeric_ids = [
            int(agent.id[1:])
            for agent in self.world.agents
            if agent.id.startswith("a") and agent.id[1:].isdigit()
        ]
        next_id = max(numeric_ids, default=0) + 1
        return f"a{next_id}"

    def _record(
        self,
        kind: str,
        actor_id: str,
        description: str,
        effects: dict[str, float],
        remember_actor: bool = True,
        remember_all: bool = False,
    ) -> Event:
        rounded_effects = {key: round(value, 3) for key, value in effects.items()}
        event = Event(
            day=self.world.day,
            kind=kind,
            actor_id=actor_id,
            description=description,
            effects=rounded_effects,
        )
        self.world.event_log.append(event)
        if remember_all:
            self._remember_all(event)
        elif remember_actor:
            actor = self._find_agent(actor_id)
            if actor is not None:
                self._remember(actor, event)
        return event

    def _remember_all(self, event: Event) -> None:
        for agent in self.world.agents:
            self._remember(agent, event)

    def _remember(self, agent: Agent, event: Event) -> None:
        agent.memories.append(f"day {event.day}: {event.description}")
        del agent.memories[:-self.world.rules.memory_limit]
        agent.memory_stream.append(memory_from_event(event, agent))
        del agent.memory_stream[:-self.world.rules.memory_stream_limit]

    def _find_agent(self, agent_id: str) -> Agent | None:
        for agent in self.world.agents:
            if agent.id == agent_id:
                return agent
        return None

    def _find_organization(self, organization_id: str) -> Organization | None:
        for organization in self.world.organizations:
            if organization.id == organization_id:
                return organization
        return None

    def _find_location(self, location_id: str) -> Location | None:
        for location in self.world.locations:
            if location.id == location_id:
                return location
        return None

    def _share_organization(self, agent: Agent, other_id: str) -> bool:
        for organization in self.world.organizations:
            if agent.id in organization.members and other_id in organization.members:
                return True
        return False

    def _agents_at_location(self, location_id: str) -> int:
        return sum(1 for agent in self.world.agents if agent.location_id == location_id)

    def _average_institutional_cohesion(self) -> float:
        if not self.world.organizations:
            return 0.0
        return sum(organization.cohesion for organization in self.world.organizations) / len(
            self.world.organizations
        )

    def _location_name(self, location_id: str) -> str:
        location = self._find_location(location_id)
        return location.name if location is not None else location_id

    def _location_production_factor(self, location_id: str, resource: str) -> float:
        location = self._find_location(location_id)
        if location is None:
            return 1.0
        return max(0.05, location.production.get(resource, 1.0))

    def _location_resource(self, location_id: str, resource: str) -> float:
        location = self._find_location(location_id)
        if location is None:
            return 0.0
        return location.resources.get(resource, 0.0)

    def _add_location_resource(self, location_id: str, resource: str, amount: float) -> float:
        location = self._find_location(location_id)
        if location is None:
            raise ValueError(f"Unknown location: {location_id}")
        before = location.resources.get(resource, 0.0)
        after = max(0.0, before + amount)
        location.resources[resource] = after
        return after - before

    def _remove_location_resource(self, location_id: str, resource: str, amount: float) -> float:
        location = self._find_location(location_id)
        if location is None:
            return 0.0
        before = location.resources.get(resource, 0.0)
        removed = min(before, max(0.0, amount))
        location.resources[resource] = before - removed
        return removed

    def _move_location_resource(
        self,
        source_id: str,
        destination_id: str,
        resource: str,
        amount: float,
    ) -> float:
        moved = self._remove_location_resource(source_id, resource, amount)
        if moved <= 0:
            return 0.0
        self._add_location_resource(destination_id, resource, moved)
        return moved

    def _remove_distributed_resource(self, resource: str, amount: float) -> float:
        remaining = max(0.0, amount)
        removed = 0.0
        for location in sorted(
            self.world.locations,
            key=lambda item: item.resources.get(resource, 0.0),
            reverse=True,
        ):
            if remaining <= 0:
                break
            change = self._remove_location_resource(location.id, resource, remaining)
            removed += change
            remaining -= change
        return removed

    def _richest_location(
        self,
        resource: str,
        exclude: set[str] | None = None,
    ) -> Location | None:
        excluded = exclude or set()
        candidates = [
            location
            for location in self.world.locations
            if location.id not in excluded and location.resources.get(resource, 0.0) > 0.05
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda location: location.resources.get(resource, 0.0))

    def _richest_reachable_location(
        self,
        resource: str,
        destination_id: str,
        exclude: set[str] | None = None,
    ) -> Location | None:
        excluded = exclude or set()
        candidates = [
            location
            for location in self.world.locations
            if location.id not in excluded
            and location.resources.get(resource, 0.0) > 0.05
            and self._route_distance(location.id, destination_id) is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda location: location.resources.get(resource, 0.0))

    def _route_distance(self, source_id: str, destination_id: str) -> int | None:
        path = self._route_path(source_id, destination_id)
        if path is None:
            return None
        return len(path) - 1

    def _route_path(self, source_id: str, destination_id: str) -> list[str] | None:
        if source_id == destination_id:
            return [source_id]
        if self._find_location(source_id) is None or self._find_location(destination_id) is None:
            return None

        visited = {source_id}
        pending: deque[list[str]] = deque([[source_id]])
        while pending:
            path = pending.popleft()
            current_id = path[-1]
            for neighbor_id in self._connected_neighbors(current_id):
                if neighbor_id in visited:
                    continue
                if neighbor_id == destination_id:
                    return [*path, neighbor_id]
                visited.add(neighbor_id)
                pending.append([*path, neighbor_id])
        return None

    def _connected_neighbors(self, location_id: str) -> list[str]:
        neighbors: set[str] = set()
        location = self._find_location(location_id)
        if location is not None:
            neighbors.update(location.connected_location_ids)
        for candidate in self.world.locations:
            if location_id in candidate.connected_location_ids:
                neighbors.add(candidate.id)
        return [
            neighbor_id
            for neighbor_id in sorted(neighbors)
            if self._find_location(neighbor_id) is not None
            and _route_key(location_id, neighbor_id) not in self.world.blocked_routes
        ]

    def _register_route_use(self, source_id: str, destination_id: str, amount: float) -> None:
        if amount <= 0.0:
            return
        path = self._route_path(source_id, destination_id)
        if path is None or len(path) < 2:
            return
        for index in range(len(path) - 1):
            route_key = _route_key(path[index], path[index + 1])
            self.world.route_loads[route_key] = self.world.route_loads.get(route_key, 0.0) + amount

    def _route_condition_factor(self, source_id: str, destination_id: str) -> float:
        path = self._route_path(source_id, destination_id)
        if path is None or len(path) < 2:
            return 1.0
        conditions = [
            self._find_location(location_id).condition
            for location_id in path
            if self._find_location(location_id) is not None
        ]
        if not conditions:
            return 1.0
        average_condition = sum(conditions) / len(conditions)
        return _clamp(0.45 + average_condition * 0.55, 0.35, 1.0)

    def _edge_condition_factor(self, route_key: str) -> float:
        location_ids = route_key.split("|")
        conditions = [
            self._find_location(location_id).condition
            for location_id in location_ids
            if self._find_location(location_id) is not None
        ]
        if not conditions:
            return 1.0
        average_condition = sum(conditions) / len(conditions)
        return _clamp(0.60 + average_condition * 0.40, 0.35, 1.0)

    def _remote_resource_total(self, resource: str, exclude: set[str]) -> float:
        return sum(
            location.resources.get(resource, 0.0)
            for location in self.world.locations
            if location.id not in exclude
        )

    def _sync_world_resources(self) -> None:
        totals = {"food": 0.0, "materials": 0.0, "shelter": 0.0}
        if self.world.locations:
            for location in self.world.locations:
                for resource in totals:
                    location.resources.setdefault(resource, 0.0)
                    totals[resource] += location.resources[resource]
            self.world.resources = totals
            return

        for resource in totals:
            self.world.resources.setdefault(resource, 0.0)

    def _wear_location(self, location_id: str, amount: float) -> None:
        location = self._find_location(location_id)
        if location is not None:
            location.condition = _clamp(location.condition - amount, 0.0, 1.0)

    def _repair_location(self, location_id: str, amount: float) -> None:
        location = self._find_location(location_id)
        if location is not None:
            location.condition = _clamp(location.condition + amount, 0.0, 1.0)


def _find_agent_in_list(agents: list[Agent], agent_id: str) -> Agent | None:
    for agent in agents:
        if agent.id == agent_id:
            return agent
    return None


def _add_connections(world: WorldState, location_id: str, neighbor_ids: list[str]) -> None:
    location = next((item for item in world.locations if item.id == location_id), None)
    if location is None:
        return
    for neighbor_id in neighbor_ids:
        if neighbor_id not in location.connected_location_ids:
            location.connected_location_ids.append(neighbor_id)


def _fill_relationships(agents: list[Agent], rng: random.Random) -> None:
    for agent in agents:
        for other in agents:
            if agent.id == other.id:
                continue
            agent.relationships.setdefault(other.id, rng.uniform(0.34, 0.66))


def _default_profile(name: str, role: str) -> AgentProfile:
    profiles = {
        "farmer": AgentProfile(
            background=f"{name} grew up reading weather, soil, and food stores as social facts.",
            values=["food security", "steady labor", "practical trust"],
            long_term_goals=["keep shared granaries dependable", "teach others resilient farming"],
            speech_style="concrete and cautious",
        ),
        "builder": AgentProfile(
            background=f"{name} learned that shelter, tools, and roads decide whether promises survive pressure.",
            values=["maintenance", "competence", "fair contribution"],
            long_term_goals=["make shelters reliable", "keep workshops stocked"],
            speech_style="direct and task focused",
        ),
        "mediator": AgentProfile(
            background=f"{name} watches how small disputes become institutional habits.",
            values=["trust", "public reasoning", "coalition repair"],
            long_term_goals=["prevent factions from hardening", "turn crises into shared norms"],
            speech_style="measured and relational",
        ),
        "forager": AgentProfile(
            background=f"{name} knows the margins of the settlement and notices weak signals early.",
            values=["adaptability", "local knowledge", "mutual aid"],
            long_term_goals=["map reliable outside resources", "warn others before scarcity spreads"],
            speech_style="observant and concise",
        ),
        "caretaker": AgentProfile(
            background=f"{name} treats fatigue, hunger, and fear as civic information.",
            values=["care", "stability", "belonging"],
            long_term_goals=["keep vulnerable residents connected", "make the shelter feel legitimate"],
            speech_style="warm but pragmatic",
        ),
        "maker": AgentProfile(
            background=f"{name} turns materials into tools and sees production as a social bargain.",
            values=["craft", "exchange", "useful invention"],
            long_term_goals=["improve tool reliability", "make trade routes worth maintaining"],
            speech_style="inventive and precise",
        ),
        "scout": AgentProfile(
            background=f"{name} moves between work sites and notices early signs of stress in routes and stores.",
            values=["warning", "adaptability", "shared maps"],
            long_term_goals=["spot shortages before they become crises", "connect distant households"],
            speech_style="brief and observational",
        ),
        "cook": AgentProfile(
            background=f"{name} sees meals as logistics, care, and politics arriving in one bowl.",
            values=["food fairness", "hospitality", "routine"],
            long_term_goals=["keep food distribution legitimate", "make common meals bind groups together"],
            speech_style="practical and hospitable",
        ),
        "healer": AgentProfile(
            background=f"{name} tracks exhaustion, fear, and injury as signals of social fragility.",
            values=["care", "patience", "early intervention"],
            long_term_goals=["prevent silent suffering", "turn the clinic into a trusted civic place"],
            speech_style="calm and attentive",
        ),
        "trader": AgentProfile(
            background=f"{name} learned that exchange routes are promises made visible.",
            values=["reciprocity", "clear bargains", "mobility"],
            long_term_goals=["make cross-household exchange predictable", "keep distant groups talking"],
            speech_style="negotiating and concise",
        ),
        "organizer": AgentProfile(
            background=f"{name} keeps track of meetings, grievances, and who has been left out.",
            values=["coordination", "legitimacy", "public memory"],
            long_term_goals=["make institutions responsive", "prevent quiet resentment from hardening"],
            speech_style="structured and diplomatic",
        ),
        "apprentice": AgentProfile(
            background=f"{name} is learning how craft, repair, and reputation fit together.",
            values=["learning", "usefulness", "recognition"],
            long_term_goals=["earn trust through visible work", "learn enough to bridge guilds"],
            speech_style="curious and direct",
        ),
    }
    return profiles.get(
        role,
        AgentProfile(
            background=f"{name} is still forming a place in the settlement.",
            values=["survival", "recognition", "learning"],
            long_term_goals=["find reliable allies", "contribute without losing autonomy"],
            speech_style="plain",
        ),
    )


def _route_key(first_location_id: str, second_location_id: str) -> str:
    left, right = sorted([first_location_id, second_location_id])
    return f"{left}|{right}"


def _relationship_key(first_agent_id: str, second_agent_id: str) -> str:
    left, right = sorted(
        [first_agent_id, second_agent_id],
        key=_agent_id_sort_key,
    )
    return f"{left}|{right}"


def _agent_id_sort_key(agent_id: str) -> tuple[str, int | str]:
    if len(agent_id) > 1 and agent_id[0].isalpha() and agent_id[1:].isdigit():
        return (agent_id[0], int(agent_id[1:]))
    return (agent_id, agent_id)


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value]
    return [str(value)]


def _float_dict(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, item in value.items():
        try:
            result[str(key)] = float(item)
        except (TypeError, ValueError):
            continue
    return result


def _normalized_intent(value: object) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "repair": "repair_routes",
        "repair_route": "repair_routes",
        "repair_routes": "repair_routes",
        "reopen_routes": "repair_routes",
        "routes": "repair_routes",
        "reconcile": "reconcile_relationships",
        "reconcile_relationships": "reconcile_relationships",
        "repair_trust": "reconcile_relationships",
        "trust": "reconcile_relationships",
        "food": "protect_food",
        "protect_food": "protect_food",
        "food_security": "protect_food",
        "coordinate": "coordinate",
        "coordination": "coordinate",
    }
    return aliases.get(raw, raw)


def _broadcast_target_text(recipients: list[Agent], agents: list[Agent]) -> str:
    if len(recipients) == len(agents):
        return "everyone"
    if not recipients:
        return "no matching agents"
    return ", ".join(agent.name for agent in recipients)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
