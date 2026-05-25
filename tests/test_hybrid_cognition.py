import unittest

from virtual_society.cognition import RuleBasedCognition
from virtual_society.hybrid_cognition import HybridCognition, HybridCognitionConfig
from virtual_society.llm_contract import PLAN_PROMPT_VERSION
from virtual_society.model import Action, Plan
from virtual_society import Simulation


class FixedProvider:
    def __init__(self, action: Action) -> None:
        self.action = action
        self.calls = 0

    def propose_plan(self, agent, world):
        self.calls += 1
        return Plan(action=self.action, priority=0.9, reason="fixed provider")


class BaselineAwareProvider(FixedProvider):
    def __init__(self, action: Action) -> None:
        super().__init__(action)
        self.baselines = []

    def propose_plan_with_baseline(self, agent, world, baseline_plan):
        self.calls += 1
        self.baselines.append(baseline_plan)
        return Plan(action=self.action, priority=0.9, reason="baseline-aware provider")


class FailingProvider:
    def __init__(self, message: str = "provider failed") -> None:
        self.calls = 0
        self.message = message

    def propose_plan(self, agent, world):
        self.calls += 1
        raise RuntimeError(self.message)


class HybridCognitionTests(unittest.TestCase):
    def test_uses_primary_only_for_selected_agent_and_day(self) -> None:
        primary = FixedProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(
                agent_ids={"a1"},
                every_days=2,
                max_calls=2,
                guard_rest_overrides=False,
            ),
        )
        simulation = Simulation(seed=7, cognition=hybrid)

        simulation.run(2)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(hybrid.stats.llm_successes, 1)
        self.assertGreater(hybrid.stats.skipped_calls, 0)
        self.assertEqual(len(hybrid.trace), 1)
        self.assertEqual(hybrid.trace[0].status, "primary")
        self.assertEqual(hybrid.trace[0].proposed_plan["action"], "rest")
        self.assertEqual(hybrid.trace[0].used_plan["action"], "rest")
        self.assertTrue(hybrid.trace[0].diverged_from_baseline)
        self.assertTrue(hybrid.trace[0].proposed_diverged_from_baseline)
        self.assertEqual(hybrid.trace[0].prompt_version, PLAN_PROMPT_VERSION)

    def test_falls_back_after_primary_failure(self) -> None:
        primary = FailingProvider()
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(agent_ids={"a1"}, every_days=1, max_calls=3, max_failures=1),
        )
        simulation = Simulation(seed=7, cognition=hybrid)

        metrics = simulation.run(2)

        self.assertEqual(metrics[-1].population, 6)
        self.assertEqual(hybrid.stats.llm_failures, 1)
        self.assertEqual(hybrid.stats.fallback_calls, 12)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(len(hybrid.trace), 1)
        self.assertEqual(hybrid.trace[0].status, "fallback_after_error")
        self.assertIsNone(hybrid.trace[0].proposed_plan)
        self.assertIn("provider failed", hybrid.trace[0].error or "")

    def test_failure_errors_are_truncated_in_trace(self) -> None:
        primary = FailingProvider("x" * 2000)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(agent_ids={"a1"}, every_days=1, max_calls=1),
        )
        simulation = Simulation(seed=7, cognition=hybrid)

        simulation.run(1)

        self.assertLess(len(hybrid.trace[0].error or ""), 700)
        self.assertIn("<truncated>", hybrid.trace[0].error or "")
        self.assertLess(len(hybrid.stats.last_errors[0]), 700)

    def test_zero_budget_never_calls_primary(self) -> None:
        primary = FixedProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(max_calls=0),
        )
        simulation = Simulation(seed=7, cognition=hybrid)

        simulation.run(3)

        self.assertEqual(primary.calls, 0)
        self.assertEqual(hybrid.stats.llm_attempts, 0)

    def test_passes_rule_baseline_to_baseline_aware_provider(self) -> None:
        primary = BaselineAwareProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(agent_ids={"a1"}, every_days=1, max_calls=1),
        )
        simulation = Simulation(seed=7, cognition=hybrid)

        simulation.run(1)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(len(primary.baselines), 1)
        self.assertIsNotNone(primary.baselines[0])

    def test_rest_override_can_fall_back_to_rule_baseline_under_pressure(self) -> None:
        primary = FixedProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(agent_ids={"a1"}, every_days=1, max_calls=1),
        )
        simulation = Simulation(seed=7, cognition=hybrid)
        simulation.world.day = 1
        simulation.world.resources["food"] = 0.0
        simulation.world.agents[0].needs.energy = 0.5
        simulation.world.agents[0].needs.food = 0.1

        hybrid.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(hybrid.trace[0].status, "baseline_after_policy")
        self.assertEqual(
            hybrid.trace[0].used_plan["action"],
            hybrid.trace[0].baseline_plan["action"],
        )
        self.assertTrue(hybrid.trace[0].proposed_diverged_from_baseline)

    def test_recent_exhaustion_block_can_justify_rest_override(self) -> None:
        primary = FixedProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(agent_ids={"a1"}, every_days=1, max_calls=1),
        )
        simulation = Simulation(seed=7, cognition=hybrid)
        simulation.world.day = 1
        simulation.world.resources["food"] = 0.0
        simulation.world.agents[0].needs.energy = 0.5
        simulation.world.agents[0].needs.food = 0.1
        simulation.world.agents[0].plan_history = [
            "day 1: gather | work plan blocked by exhaustion; resting first",
            "day 2: farm | shared food stores are low",
        ]

        hybrid.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(hybrid.trace[0].status, "primary")
        self.assertEqual(hybrid.trace[0].used_plan["action"], "rest")
        self.assertTrue(hybrid.trace[0].diverged_from_baseline)

    def test_counterfactual_policy_can_reject_lower_scoring_plan(self) -> None:
        primary = FixedProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(
                agent_ids={"a1"},
                every_days=1,
                max_calls=1,
                guard_rest_overrides=False,
                counterfactual_horizon_days=3,
                counterfactual_reject_threshold=0.02,
            ),
        )
        simulation = Simulation(seed=7, cognition=hybrid, world_preset="generative_alpha")
        simulation.world.day = 21
        simulation.world.resources["food"] = 0.0
        for location in simulation.world.locations:
            location.resources["food"] = 0.0
        simulation.world.agents[0].needs.food = 0.8
        simulation.world.agents[0].needs.energy = 0.9

        plan = hybrid.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(plan.action, Action.FARM)
        self.assertEqual(hybrid.trace[0].status, "baseline_after_counterfactual")
        self.assertEqual(hybrid.trace[0].used_plan["action"], "farm")
        self.assertEqual(hybrid.trace[0].proposed_plan["action"], "rest")
        self.assertEqual(hybrid.trace[0].counterfactual["recommendation"], "baseline")
        self.assertLess(hybrid.trace[0].counterfactual["score_delta"], -0.02)


if __name__ == "__main__":
    unittest.main()
