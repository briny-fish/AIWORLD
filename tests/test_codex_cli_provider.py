import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from virtual_society import LLMCallCache, Simulation
from virtual_society.codex_cli_provider import (
    CodexCliCognition,
    CodexCliCognitionError,
    CodexCliDialogue,
    CodexCliReflection,
)
from virtual_society.model import Action
from virtual_society.reflection import RuleBasedReflection


class CodexCliProviderTests(unittest.TestCase):
    def test_provider_parses_plan_from_output_file(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            output_path = command[command.index("--output-last-message") + 1]
            Path(output_path).write_text(
                '{"action":"farm","priority":0.7,"reason":"food is low","target_id":null,"horizon_days":1}',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        simulation = Simulation(seed=7)
        provider = CodexCliCognition(
            codex_path="codex.exe",
            model="gpt-5.4-mini",
            reasoning_effort="low",
            run_command=fake_run,
        )

        plan = provider.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(plan.action, Action.FARM)
        self.assertEqual(plan.reason, "food is low")
        self.assertIn("gpt-5.4-mini", commands[0])
        self.assertIn('model_reasoning_effort="low"', commands[0])
        self.assertIn("decision_pressure", commands[0][-1])
        self.assertIn("exhaustion_work_threshold", commands[0][-1])
        self.assertNotIn("relationship_daily_drift", commands[0][-1])

    def test_provider_can_include_baseline_plan_in_prompt(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            output_path = command[command.index("--output-last-message") + 1]
            Path(output_path).write_text(
                '{"action":"rest","priority":0.6,"reason":"energy is low","target_id":null,"horizon_days":1}',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        simulation = Simulation(seed=7)
        baseline = simulation.world.agents[0].active_plan
        if baseline is None:
            from virtual_society.cognition import RuleBasedCognition

            baseline = RuleBasedCognition().propose_plan(
                simulation.world.agents[0],
                simulation.world,
            )
        provider = CodexCliCognition(codex_path="codex.exe", run_command=fake_run)

        provider.propose_plan_with_baseline(
            simulation.world.agents[0],
            simulation.world,
            baseline,
        )

        self.assertIn('"baseline_plan"', commands[0][-1])
        self.assertIn(baseline.action.value, commands[0][-1])

    def test_provider_rejects_failed_codex_call(self) -> None:
        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed")

        simulation = Simulation(seed=7)
        provider = CodexCliCognition(codex_path="codex.exe", run_command=fake_run)

        with self.assertRaises(CodexCliCognitionError):
            provider.propose_plan(simulation.world.agents[0], simulation.world)

    def test_provider_rejects_invalid_plan_json(self) -> None:
        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            output_path = command[command.index("--output-last-message") + 1]
            Path(output_path).write_text('{"action":"unknown","reason":"bad"}', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        simulation = Simulation(seed=7)
        provider = CodexCliCognition(codex_path="codex.exe", run_command=fake_run)

        with self.assertRaises(CodexCliCognitionError):
            provider.propose_plan(simulation.world.agents[0], simulation.world)

    def test_provider_replays_cached_plan_without_invoking_codex(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            output_path = command[command.index("--output-last-message") + 1]
            Path(output_path).write_text(
                '{"action":"farm","priority":0.7,"reason":"cached food plan","target_id":null,"horizon_days":1}',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with TemporaryDirectory() as directory:
            simulation = Simulation(seed=7)
            cache = LLMCallCache(directory)
            provider = CodexCliCognition(
                codex_path="codex.exe",
                cache=cache,
                run_command=fake_run,
            )

            first = provider.propose_plan(simulation.world.agents[0], simulation.world)
            second = provider.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(first.reason, "cached food plan")
        self.assertEqual(second.reason, "cached food plan")
        self.assertEqual(len(commands), 1)
        self.assertEqual(cache.stats.writes, 1)
        self.assertEqual(cache.stats.hits, 1)

    def test_provider_read_only_cache_miss_does_not_invoke_codex(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with TemporaryDirectory() as directory:
            simulation = Simulation(seed=7)
            cache = LLMCallCache(directory, mode="read-only")
            provider = CodexCliCognition(
                codex_path="codex.exe",
                cache=cache,
                run_command=fake_run,
            )

            with self.assertRaises(CodexCliCognitionError):
                provider.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(commands, [])

    def test_reflection_provider_parses_memory_grounded_output(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            output_path = command[command.index("--output-last-message") + 1]
            Path(output_path).write_text(
                '{"summary":"Ari connected field work with food pressure.","focus":"work","memory_refs":[0]}',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        simulation = Simulation(seed=7)
        simulation.run(1)
        agent = simulation.world.agents[0]
        baseline = RuleBasedReflection().propose_reflection(
            agent,
            simulation.world,
            current_day=simulation.world.day,
            lookback_days=1,
        )
        provider = CodexCliReflection(codex_path="codex.exe", run_command=fake_run)

        proposal = provider.propose_reflection_with_baseline(
            agent,
            simulation.world,
            current_day=simulation.world.day,
            lookback_days=1,
            baseline=baseline,
        )

        self.assertEqual(proposal.focus, "work")
        self.assertEqual(proposal.memory_refs, [0])
        self.assertIn("recent_memories", commands[0][-1])
        self.assertIn("baseline_reflection", commands[0][-1])

    def test_dialogue_provider_parses_memory_grounded_output(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            output_path = command[command.index("--output-last-message") + 1]
            Path(output_path).write_text(
                '{"text":"Ari asked Bo to keep food distribution visible.","focus":"coordination","memory_refs":[0]}',
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        simulation = Simulation(seed=7)
        simulation.run(1)
        speaker = simulation.world.agents[0]
        partner = simulation.world.agents[1]
        provider = CodexCliDialogue(codex_path="codex.exe", run_command=fake_run)

        proposal = provider.propose_dialogue(
            speaker,
            partner,
            simulation.world,
            "Ari and Bo discussed routine work.",
        )

        self.assertEqual(proposal.focus, "coordination")
        self.assertEqual(proposal.memory_refs, [0])
        self.assertIn("recent_memories", commands[0][-1])
        self.assertIn("baseline_dialogue", commands[0][-1])


if __name__ == "__main__":
    unittest.main()
