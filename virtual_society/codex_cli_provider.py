from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .dialogue_contract import (
    DialogueProposal,
    build_dialogue_context,
    parse_dialogue_response,
    render_dialogue_prompt,
)
from .llm_contract import build_cognition_context, parse_plan_response, render_plan_prompt
from .model import Agent, Plan, WorldState
from .reflection_contract import (
    ReflectionProposal,
    build_reflection_context,
    parse_reflection_response,
    render_reflection_prompt,
)


class CodexCliCognitionError(RuntimeError):
    pass


RunCommand = Callable[[list[str], int], subprocess.CompletedProcess[str]]


class CodexCliCognition:
    """Cognition provider backed by local `codex exec`.

    This uses the user's existing Codex login instead of an API key. It is
    intentionally optional because a process-per-plan call is expensive.
    """

    def __init__(
        self,
        codex_path: str | None = None,
        model: str = "gpt-5.4-mini",
        reasoning_effort: str = "low",
        timeout_seconds: int = 180,
        workdir: str | None = None,
        run_command: RunCommand | None = None,
    ) -> None:
        self.codex_path = codex_path or resolve_codex_cli()
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.workdir = workdir
        self._run_command = run_command or self._default_run_command

    def propose_plan(self, agent: Agent, world: WorldState) -> Plan:
        return self.propose_plan_with_baseline(agent, world, None)

    def propose_plan_with_baseline(
        self,
        agent: Agent,
        world: WorldState,
        baseline_plan: Plan | None,
    ) -> Plan:
        context = build_cognition_context(agent, world, baseline_plan=baseline_plan)
        prompt = (
            f"{render_plan_prompt(context)}\n\n"
            "Return JSON only. No markdown. No prose before or after the JSON."
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = str(Path(directory) / "codex-plan.json")
            command = self._build_command(output_path, prompt)
            result = self._run_command(command, self.timeout_seconds)

            if result.returncode != 0:
                raise CodexCliCognitionError(
                    "codex exec failed: "
                    f"{_truncate(result.stderr or result.stdout or 'no output')}"
                )

            if not Path(output_path).exists():
                raise CodexCliCognitionError("codex exec did not write an output message")

            response = Path(output_path).read_text(encoding="utf-8")

        try:
            return parse_plan_response(_loads_json_object(response))
        except Exception as exc:
            raise CodexCliCognitionError(
                f"codex exec returned an invalid plan: {_truncate(response)}"
            ) from exc

    def _build_command(self, output_path: str, prompt: str) -> list[str]:
        command = [
            self.codex_path,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "-m",
            self.model,
            "-c",
            f'model_reasoning_effort="{self.reasoning_effort}"',
            "--output-last-message",
            output_path,
        ]
        if self.workdir is not None:
            command.extend(["-C", self.workdir])
        command.append(prompt)
        return command

    def _default_run_command(
        self,
        command: list[str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )


class CodexCliReflection:
    """Reflection provider backed by local `codex exec`."""

    def __init__(
        self,
        codex_path: str | None = None,
        model: str = "gpt-5.4-mini",
        reasoning_effort: str = "low",
        timeout_seconds: int = 180,
        workdir: str | None = None,
        run_command: RunCommand | None = None,
    ) -> None:
        self.codex_path = codex_path or resolve_codex_cli()
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.workdir = workdir
        self._run_command = run_command or self._default_run_command

    def propose_reflection(
        self,
        agent: Agent,
        world: WorldState,
        current_day: int,
        lookback_days: int,
    ) -> ReflectionProposal:
        return self.propose_reflection_with_baseline(
            agent,
            world,
            current_day,
            lookback_days,
            ReflectionProposal(summary="", focus="routine"),
        )

    def propose_reflection_with_baseline(
        self,
        agent: Agent,
        world: WorldState,
        current_day: int,
        lookback_days: int,
        baseline: ReflectionProposal,
    ) -> ReflectionProposal:
        context = build_reflection_context(
            agent,
            world,
            current_day,
            lookback_days,
            baseline.summary,
        )
        prompt = (
            f"{render_reflection_prompt(context)}\n\n"
            "Return JSON only. No markdown. No prose before or after the JSON."
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = str(Path(directory) / "codex-reflection.json")
            command = self._build_command(output_path, prompt)
            result = self._run_command(command, self.timeout_seconds)

            if result.returncode != 0:
                raise CodexCliCognitionError(
                    "codex exec failed: "
                    f"{_truncate(result.stderr or result.stdout or 'no output')}"
                )
            if not Path(output_path).exists():
                raise CodexCliCognitionError("codex exec did not write an output message")
            response = Path(output_path).read_text(encoding="utf-8")

        try:
            return parse_reflection_response(
                _loads_json_object(response),
                memory_count=len(context.recent_memories),
            )
        except Exception as exc:
            raise CodexCliCognitionError(
                f"codex exec returned an invalid reflection: {_truncate(response)}"
            ) from exc

    def _build_command(self, output_path: str, prompt: str) -> list[str]:
        command = [
            self.codex_path,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "-m",
            self.model,
            "-c",
            f'model_reasoning_effort="{self.reasoning_effort}"',
            "--output-last-message",
            output_path,
        ]
        if self.workdir is not None:
            command.extend(["-C", self.workdir])
        command.append(prompt)
        return command

    def _default_run_command(
        self,
        command: list[str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )


class CodexCliDialogue:
    """Dialogue provider backed by local `codex exec`."""

    def __init__(
        self,
        codex_path: str | None = None,
        model: str = "gpt-5.4-mini",
        reasoning_effort: str = "low",
        timeout_seconds: int = 180,
        workdir: str | None = None,
        run_command: RunCommand | None = None,
    ) -> None:
        self.codex_path = codex_path or resolve_codex_cli()
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.workdir = workdir
        self._run_command = run_command or self._default_run_command

    def propose_dialogue(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline_dialogue: str,
    ) -> DialogueProposal:
        return self.propose_dialogue_with_baseline(
            speaker,
            partner,
            world,
            DialogueProposal(text=baseline_dialogue),
        )

    def propose_dialogue_with_baseline(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline: DialogueProposal,
    ) -> DialogueProposal:
        context = build_dialogue_context(speaker, partner, world, baseline.text)
        prompt = (
            f"{render_dialogue_prompt(context)}\n\n"
            "Return JSON only. No markdown. No prose before or after the JSON."
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = str(Path(directory) / "codex-dialogue.json")
            command = self._build_command(output_path, prompt)
            result = self._run_command(command, self.timeout_seconds)

            if result.returncode != 0:
                raise CodexCliCognitionError(
                    "codex exec failed: "
                    f"{_truncate(result.stderr or result.stdout or 'no output')}"
                )
            if not Path(output_path).exists():
                raise CodexCliCognitionError("codex exec did not write an output message")
            response = Path(output_path).read_text(encoding="utf-8")

        try:
            return parse_dialogue_response(
                _loads_json_object(response),
                memory_count=len(context.recent_memories),
            )
        except Exception as exc:
            raise CodexCliCognitionError(
                f"codex exec returned an invalid dialogue: {_truncate(response)}"
            ) from exc

    def _build_command(self, output_path: str, prompt: str) -> list[str]:
        command = [
            self.codex_path,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "-m",
            self.model,
            "-c",
            f'model_reasoning_effort="{self.reasoning_effort}"',
            "--output-last-message",
            output_path,
        ]
        if self.workdir is not None:
            command.extend(["-C", self.workdir])
        command.append(prompt)
        return command

    def _default_run_command(
        self,
        command: list[str],
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )


def resolve_codex_cli() -> str:
    configured = os.environ.get("VIRTUAL_SOCIETY_CODEX_CLI")
    if configured:
        return configured

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        sandbox_bin = Path(user_profile) / ".codex" / ".sandbox-bin" / "codex.exe"
        if sandbox_bin.exists():
            return str(sandbox_bin)

    discovered = shutil.which("codex")
    if discovered:
        return discovered

    raise CodexCliCognitionError(
        "Could not find Codex CLI. Set VIRTUAL_SOCIETY_CODEX_CLI to codex.exe."
    )


def _loads_json_object(value: str) -> dict:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _truncate(value: str, limit: int = 1000) -> str:
    compact = value.strip().replace("\r\n", "\n")
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "... <truncated>"
