from __future__ import annotations

from typing import Protocol

from .generative_memory import retrieve_memories
from .model import Action, Agent, Plan, WorldState


class CognitionProvider(Protocol):
    def propose_plan(self, agent: Agent, world: WorldState) -> Plan:
        """Return a candidate plan. The simulation core still validates it."""


class RuleBasedCognition:
    """Deterministic cognition provider used until an external LLM is configured."""

    def propose_plan(self, agent: Agent, world: WorldState) -> Plan:
        scores = {
            Action.FARM: 0.05,
            Action.GATHER: 0.05,
            Action.HAUL: 0.05,
            Action.REST: 0.05,
            Action.SOCIALIZE: 0.05,
            Action.REPAIR: 0.05,
        }
        reasons: dict[Action, list[str]] = {action: [] for action in scores}

        self._score_needs(agent, world, scores, reasons)
        self._score_role_bias(agent, scores, reasons)
        self._score_memory_bias(agent, world, scores, reasons)
        self._score_social_context(agent, scores, reasons)
        self._score_institutional_context(agent, world, scores, reasons)

        action = max(
            scores,
            key=lambda candidate: (scores[candidate], -_action_order(candidate)),
        )
        target_id = self._select_target(agent, action)
        reason = "; ".join(reasons[action]) or "default routine"
        return Plan(
            action=action,
            priority=round(scores[action], 3),
            reason=reason,
            target_id=target_id,
        )

    def _score_needs(
        self,
        agent: Agent,
        world: WorldState,
        scores: dict[Action, float],
        reasons: dict[Action, list[str]],
    ) -> None:
        food_pressure = world.population * world.rules.food_per_agent * 1.15
        if agent.needs.food < 0.45:
            scores[Action.FARM] += (0.45 - agent.needs.food) * 2.4
            reasons[Action.FARM].append("personal food need is low")
        food_stores = world.resources.get("food", 0.0)
        if food_stores < food_pressure:
            pressure = (food_pressure - food_stores) / max(food_pressure, 0.1)
            scores[Action.FARM] += 0.75 + pressure * 1.15
            reasons[Action.FARM].append("shared food stores are low")
        depot_food = _location_resource(world, "commons", "food") + _location_resource(
            world,
            "shelter_house",
            "food",
        )
        depot_target = world.population * world.rules.food_per_agent * world.rules.depot_food_target_days
        remote_food = food_stores - depot_food
        if depot_food < depot_target and remote_food > world.population * 0.25:
            pressure = (depot_target - depot_food) / max(depot_target, 0.1)
            scores[Action.HAUL] += 1.05 + pressure * 1.45
            reasons[Action.HAUL].append("food needs hauling to shared depots")
            if agent.needs.food < 0.55:
                scores[Action.HAUL] += 0.45
                reasons[Action.HAUL].append("personal food need depends on depot logistics")

        if agent.needs.energy < 0.36:
            scores[Action.REST] += (0.36 - agent.needs.energy) * 1.5
            reasons[Action.REST].append("energy is low")

        shelter_floor = world.population * world.rules.shelter_safety_ratio
        if agent.needs.safety < 0.48:
            scores[Action.REPAIR] += (0.48 - agent.needs.safety) * 2.0
            reasons[Action.REPAIR].append("safety need is low")
        if world.resources.get("shelter", 0.0) < shelter_floor:
            scores[Action.REPAIR] += 0.55
            reasons[Action.REPAIR].append("shared shelter is insufficient")

        if world.resources.get("materials", 0.0) < world.population * 0.35:
            scores[Action.GATHER] += 0.30
            reasons[Action.GATHER].append("materials are depleted")
        workshop_materials = _location_resource(world, "workshop", "materials")
        if (
            workshop_materials < world.rules.workshop_material_target
            and world.resources.get("materials", 0.0) > workshop_materials + 0.30
        ):
            scores[Action.HAUL] += 0.28
            reasons[Action.HAUL].append("materials need hauling to the workshop")

        if agent.needs.belonging < 0.48:
            scores[Action.SOCIALIZE] += (0.48 - agent.needs.belonging) * 2.0
            reasons[Action.SOCIALIZE].append("belonging need is low")
        if agent.needs.meaning < 0.42:
            scores[Action.SOCIALIZE] += 0.12
            scores[Action.GATHER] += 0.08
            reasons[Action.SOCIALIZE].append("meaning need is low")

    def _score_role_bias(
        self,
        agent: Agent,
        scores: dict[Action, float],
        reasons: dict[Action, list[str]],
    ) -> None:
        role_bias = {
            "farmer": Action.FARM,
            "forager": Action.GATHER,
            "builder": Action.REPAIR,
            "maker": Action.GATHER,
            "mediator": Action.SOCIALIZE,
            "caretaker": Action.SOCIALIZE,
            "scout": Action.GATHER,
            "carrier": Action.HAUL,
            "cook": Action.HAUL,
            "healer": Action.SOCIALIZE,
            "trader": Action.HAUL,
            "organizer": Action.SOCIALIZE,
            "apprentice": Action.REPAIR,
        }
        action = role_bias.get(agent.role)
        if action is None:
            return
        scores[action] += 0.10
        reasons[action].append(f"role bias: {agent.role}")

    def _score_memory_bias(
        self,
        agent: Agent,
        world: WorldState,
        scores: dict[Action, float],
        reasons: dict[Action, list[str]],
    ) -> None:
        retrieved = retrieve_memories(
            agent,
            "food scarcity hunger disaster damage repair hope exchange trust",
            current_day=world.day,
            limit=8,
        )
        recent_memory = " ".join(memory.text for memory in retrieved).lower()
        if not recent_memory:
            recent_memory = " ".join(agent.memories[-8:]).lower()
        recent_events = " ".join(event.description for event in world.event_log[-12:]).lower()
        context = f"{recent_memory} {recent_events}"

        if "went hungry" in context or "food scarcity" in context:
            scores[Action.FARM] += 0.35
            reasons[Action.FARM].append("recent memory includes hunger or scarcity")
            depot_food = _location_resource(world, "commons", "food") + _location_resource(
                world,
                "shelter_house",
                "food",
            )
            remote_food = world.resources.get("food", 0.0) - depot_food
            if remote_food > world.population * 0.25:
                scores[Action.HAUL] += 0.35
                reasons[Action.HAUL].append("recent memory includes hunger and remote food")
        if "disaster" in context or "storm" in context or "damaged" in context:
            scores[Action.REPAIR] += 0.16
            reasons[Action.REPAIR].append("recent memory includes damage")
        if "broadcast hope" in context or "recover together" in context:
            scores[Action.SOCIALIZE] += 0.08
            reasons[Action.SOCIALIZE].append("recent hopeful message favors coordination")

    def _score_social_context(
        self,
        agent: Agent,
        scores: dict[Action, float],
        reasons: dict[Action, list[str]],
    ) -> None:
        if not agent.relationships:
            return
        average_trust = sum(agent.relationships.values()) / len(agent.relationships)
        if average_trust < 0.42:
            scores[Action.SOCIALIZE] += 0.25
            reasons[Action.SOCIALIZE].append("average trust is weak")
        elif average_trust > 0.68:
            scores[Action.FARM] += 0.05
            scores[Action.REPAIR] += 0.05
            reasons[Action.FARM].append("high trust supports coordinated work")
            reasons[Action.REPAIR].append("high trust supports coordinated work")

    def _score_institutional_context(
        self,
        agent: Agent,
        world: WorldState,
        scores: dict[Action, float],
        reasons: dict[Action, list[str]],
    ) -> None:
        if agent.reputation < 0.42:
            scores[Action.SOCIALIZE] += 0.10
            scores[Action.FARM] += 0.05
            scores[Action.REPAIR] += 0.05
            reasons[Action.SOCIALIZE].append("reputation is weak")
            reasons[Action.FARM].append("reputation is weak")
            reasons[Action.REPAIR].append("reputation is weak")

        if not world.organizations or not agent.organization_ids:
            return

        organization_cohesion = [
            organization.cohesion
            for organization in world.organizations
            if organization.id in agent.organization_ids
        ]
        if not organization_cohesion:
            return

        average_cohesion = sum(organization_cohesion) / len(organization_cohesion)
        if average_cohesion < 0.45:
            scores[Action.SOCIALIZE] += 0.18
            scores[Action.HAUL] += 0.05
            scores[Action.REPAIR] += 0.06
            reasons[Action.SOCIALIZE].append("organization cohesion is weak")
            reasons[Action.HAUL].append("organization cohesion is weak")
            reasons[Action.REPAIR].append("organization cohesion is weak")
        elif average_cohesion > 0.70:
            scores[Action.FARM] += 0.04
            scores[Action.REPAIR] += 0.04
            reasons[Action.FARM].append("strong institutions support coordinated work")
            reasons[Action.REPAIR].append("strong institutions support coordinated work")

    def _select_target(self, agent: Agent, action: Action) -> str | None:
        if action != Action.SOCIALIZE or not agent.relationships:
            return None
        return min(agent.relationships, key=lambda other_id: agent.relationships[other_id])


def _action_order(action: Action) -> int:
    order = {
        Action.FARM: 0,
        Action.HAUL: 1,
        Action.REPAIR: 2,
        Action.REST: 3,
        Action.SOCIALIZE: 4,
        Action.GATHER: 5,
    }
    return order[action]


def _location_resource(world: WorldState, location_id: str, resource: str) -> float:
    for location in world.locations:
        if location.id == location_id:
            return location.resources.get(resource, 0.0)
    return 0.0
