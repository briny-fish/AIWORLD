import unittest

from virtual_society.cognition import RuleBasedCognition
from virtual_society.hybrid_cognition import HybridCognition, HybridCognitionConfig
from virtual_society.model import Action, Plan
from virtual_society import Simulation


class FixedProvider:
    def __init__(self, action: Action) -> None:
        self.action = action
        self.calls = 0

    def propose_plan(self, agent, world):
        self.calls += 1
        return Plan(action=self.action, priority=0.9, reason="fixed provider")


class FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def propose_plan(self, agent, world):
        self.calls += 1
        raise RuntimeError("provider failed")


class HybridCognitionTests(unittest.TestCase):
    def test_uses_primary_only_for_selected_agent_and_day(self) -> None:
        primary = FixedProvider(Action.REST)
        hybrid = HybridCognition(
            primary=primary,
            fallback=RuleBasedCognition(),
            config=HybridCognitionConfig(agent_ids={"a1"}, every_days=2, max_calls=2),
        )
        simulation = Simulation(seed=7, cognition=hybrid)

        simulation.run(2)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(hybrid.stats.llm_successes, 1)
        self.assertGreater(hybrid.stats.skipped_calls, 0)

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


if __name__ == "__main__":
    unittest.main()

