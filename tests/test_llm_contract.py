import unittest

from virtual_society.llm_contract import (
    PLAN_PROMPT_VERSION,
    PlanParseError,
    build_cognition_context,
    parse_plan_response,
    render_plan_prompt,
)
from virtual_society.interventions import Intervention
from virtual_society.model import Action
from virtual_society import Simulation


class LLMContractTests(unittest.TestCase):
    def test_context_is_json_ready_and_contains_allowed_actions(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(3)
        agent = simulation.world.agents[0]

        context = build_cognition_context(agent, simulation.world)

        self.assertIn(Action.FARM.value, context.allowed_actions)
        self.assertEqual(context.prompt_version, PLAN_PROMPT_VERSION)
        self.assertEqual(context.agent["id"], agent.id)
        self.assertEqual(context.world["day"], 3)
        self.assertIn("profile", context.agent)
        self.assertIn("reputation", context.agent)
        self.assertIn("location_id", context.agent)
        self.assertIn("retrieved_memories", context.as_dict())
        self.assertIn("decision_pressure", context.as_dict())
        self.assertIn("recent_life_journal", context.agent)
        self.assertTrue(context.agent["recent_life_journal"])
        self.assertIn("food_gap", context.decision_pressure)
        self.assertIn("active_relationship_crises", context.decision_pressure)
        self.assertIn("organization_pressures", context.decision_pressure)
        self.assertIn("remembered_observer_intents", context.decision_pressure)
        self.assertIn("blocked_routes", context.decision_pressure)
        self.assertTrue(context.world["locations"])
        self.assertTrue(context.world["agent_organizations"])

    def test_prompt_instructs_structured_plan_output(self) -> None:
        simulation = Simulation(seed=7)
        context = build_cognition_context(simulation.world.agents[0], simulation.world)

        prompt = render_plan_prompt(context)

        self.assertIn("Return exactly one JSON object", prompt)
        self.assertIn(PLAN_PROMPT_VERSION, prompt)
        self.assertIn("allowed_actions", prompt)
        self.assertIn("Use target_id only for socialize plans", prompt)
        self.assertIn("baseline_plan", prompt)
        self.assertIn("shared production and repair needs", prompt)
        self.assertIn("active_relationship_crises", prompt)
        self.assertIn("recent_life_journal", prompt)

    def test_context_can_include_rule_baseline_plan(self) -> None:
        simulation = Simulation(seed=7)
        agent = simulation.world.agents[0]
        baseline = agent.active_plan
        if baseline is None:
            from virtual_society.cognition import RuleBasedCognition

            baseline = RuleBasedCognition().propose_plan(agent, simulation.world)

        context = build_cognition_context(agent, simulation.world, baseline_plan=baseline)

        self.assertIsNotNone(context.baseline_plan)
        self.assertEqual(context.baseline_plan["action"], baseline.action.value)
        self.assertEqual(
            context.decision_pressure["baseline_action"],
            baseline.action.value,
        )

    def test_compact_context_keeps_decision_facts_without_full_rules(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(3)
        agent = simulation.world.agents[0]

        full = build_cognition_context(agent, simulation.world)
        compact = build_cognition_context(agent, simulation.world, compact=True)

        self.assertIn("exhaustion_work_threshold", compact.world["rules"])
        self.assertNotIn("relationship_daily_drift", compact.world["rules"])
        self.assertIn("connected_location_ids", compact.world["locations"][0])
        self.assertNotIn("production", compact.world["locations"][0])
        self.assertLess(len(render_plan_prompt(compact)), len(render_plan_prompt(full)))

    def test_decision_pressure_exposes_social_history_and_observer_intent(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.relationship_crises["a1|a2"] = 1
        simulation.run(
            1,
            interventions=[
                Intervention(
                    day=1,
                    kind="broadcast",
                    params={
                        "intent": "reconcile_relationships",
                        "target_agent_ids": ["a1"],
                        "message": "Ari, repair trust with Bo.",
                    },
                )
            ],
        )
        agent = simulation.world.agents[0]

        context = build_cognition_context(agent, simulation.world)

        crises = context.decision_pressure["active_relationship_crises"]
        self.assertEqual(crises[0]["other_agent_id"], "a2")
        self.assertEqual(crises[0]["other_agent_name"], "Bo")
        intents = context.decision_pressure["remembered_observer_intents"]
        self.assertEqual(intents[0]["intent"], "reconcile_relationships")
        self.assertTrue(context.decision_pressure["weakest_relationships"])

    def test_parse_plan_response_accepts_valid_plan(self) -> None:
        plan = parse_plan_response(
            {
                "action": "farm",
                "priority": 0.8,
                "reason": "food stores are low",
                "target_id": None,
                "horizon_days": 1,
            }
        )

        self.assertEqual(plan.action, Action.FARM)
        self.assertEqual(plan.priority, 0.8)

    def test_parse_plan_response_drops_non_social_targets(self) -> None:
        plan = parse_plan_response(
            {
                "action": "rest",
                "priority": 0.8,
                "reason": "energy is exhausted",
                "target_id": "self",
                "horizon_days": 1,
            }
        )

        self.assertEqual(plan.action, Action.REST)
        self.assertIsNone(plan.target_id)

    def test_parse_plan_response_keeps_social_targets(self) -> None:
        plan = parse_plan_response(
            {
                "action": "socialize",
                "priority": 0.6,
                "reason": "repair trust",
                "target_id": "a3",
                "horizon_days": 1,
            }
        )

        self.assertEqual(plan.action, Action.SOCIALIZE)
        self.assertEqual(plan.target_id, "a3")

    def test_parse_plan_response_rejects_invalid_action(self) -> None:
        with self.assertRaises(PlanParseError):
            parse_plan_response({"action": "invent_magic", "reason": "invalid"})


if __name__ == "__main__":
    unittest.main()
