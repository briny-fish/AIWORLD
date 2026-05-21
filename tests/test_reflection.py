import unittest

from virtual_society import Simulation
from virtual_society.reflection import (
    HybridReflection,
    HybridReflectionConfig,
    RuleBasedReflection,
)
from virtual_society.reflection_contract import ReflectionProposal


class FixedReflection:
    def __init__(self) -> None:
        self.calls = 0

    def propose_reflection(self, agent, world, current_day, lookback_days):
        self.calls += 1
        return ReflectionProposal(
            summary=f"{agent.name} tied recent work to a longer goal.",
            focus="identity",
            memory_refs=[0],
        )


class BaselineAwareReflection(FixedReflection):
    def __init__(self) -> None:
        super().__init__()
        self.baselines = []

    def propose_reflection_with_baseline(
        self,
        agent,
        world,
        current_day,
        lookback_days,
        baseline,
    ):
        self.calls += 1
        self.baselines.append(baseline)
        return ReflectionProposal(
            summary=f"{agent.name} sharpened the baseline reflection.",
            focus="work",
            memory_refs=[0],
        )


class FailingReflection:
    def __init__(self) -> None:
        self.calls = 0

    def propose_reflection(self, agent, world, current_day, lookback_days):
        self.calls += 1
        raise RuntimeError("reflection provider failed")


class HybridReflectionTests(unittest.TestCase):
    def test_uses_primary_only_for_selected_agent_and_reflection_day(self) -> None:
        primary = FixedReflection()
        hybrid = HybridReflection(
            primary=primary,
            fallback=RuleBasedReflection(),
            config=HybridReflectionConfig(agent_ids={"a1"}, min_day=7, max_calls=1),
        )
        simulation = Simulation(seed=7, reflection=hybrid)

        simulation.run(7)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(hybrid.stats.llm_successes, 1)
        self.assertGreater(hybrid.stats.skipped_calls, 0)
        self.assertEqual(len(hybrid.trace), 1)
        self.assertEqual(hybrid.trace[0].status, "primary")
        self.assertEqual(hybrid.trace[0].focus, "identity")
        self.assertEqual(hybrid.trace[0].memory_refs, [0])
        self.assertIn("longer goal", hybrid.trace[0].used_reflection)

    def test_falls_back_after_primary_failure(self) -> None:
        primary = FailingReflection()
        hybrid = HybridReflection(
            primary=primary,
            fallback=RuleBasedReflection(),
            config=HybridReflectionConfig(agent_ids={"a1"}, min_day=7, max_calls=2, max_failures=1),
        )
        simulation = Simulation(seed=7, reflection=hybrid)

        metrics = simulation.run(7)

        self.assertEqual(metrics[-1].population, 6)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(hybrid.stats.llm_failures, 1)
        self.assertEqual(hybrid.stats.fallback_calls, 6)
        self.assertEqual(hybrid.trace[0].status, "fallback_after_error")
        self.assertIsNone(hybrid.trace[0].proposed_reflection)
        self.assertIn("reflection provider failed", hybrid.trace[0].error or "")

    def test_passes_rule_baseline_to_baseline_aware_provider(self) -> None:
        primary = BaselineAwareReflection()
        hybrid = HybridReflection(
            primary=primary,
            fallback=RuleBasedReflection(),
            config=HybridReflectionConfig(agent_ids={"a1"}, min_day=7, max_calls=1),
        )
        simulation = Simulation(seed=7, reflection=hybrid)

        simulation.run(7)

        self.assertEqual(primary.calls, 1)
        self.assertEqual(len(primary.baselines), 1)
        self.assertTrue(primary.baselines[0].summary)


if __name__ == "__main__":
    unittest.main()
