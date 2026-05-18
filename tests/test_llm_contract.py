import unittest

from virtual_society.llm_contract import (
    PlanParseError,
    build_cognition_context,
    parse_plan_response,
    render_plan_prompt,
)
from virtual_society.model import Action
from virtual_society import Simulation


class LLMContractTests(unittest.TestCase):
    def test_context_is_json_ready_and_contains_allowed_actions(self) -> None:
        simulation = Simulation(seed=7)
        simulation.run(3)
        agent = simulation.world.agents[0]

        context = build_cognition_context(agent, simulation.world)

        self.assertIn(Action.FARM.value, context.allowed_actions)
        self.assertEqual(context.agent["id"], agent.id)
        self.assertEqual(context.world["day"], 3)
        self.assertIn("profile", context.agent)
        self.assertIn("reputation", context.agent)
        self.assertIn("location_id", context.agent)
        self.assertIn("retrieved_memories", context.as_dict())
        self.assertTrue(context.world["locations"])
        self.assertTrue(context.world["agent_organizations"])

    def test_prompt_instructs_structured_plan_output(self) -> None:
        simulation = Simulation(seed=7)
        context = build_cognition_context(simulation.world.agents[0], simulation.world)

        prompt = render_plan_prompt(context)

        self.assertIn("Return exactly one JSON object", prompt)
        self.assertIn("allowed_actions", prompt)

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

    def test_parse_plan_response_rejects_invalid_action(self) -> None:
        with self.assertRaises(PlanParseError):
            parse_plan_response({"action": "invent_magic", "reason": "invalid"})


if __name__ == "__main__":
    unittest.main()
