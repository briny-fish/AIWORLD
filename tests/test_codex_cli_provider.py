import subprocess
import unittest
from pathlib import Path

from virtual_society import Simulation
from virtual_society.codex_cli_provider import CodexCliCognition, CodexCliCognitionError
from virtual_society.model import Action


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


if __name__ == "__main__":
    unittest.main()

