from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .dialogue_contract import (
    DialogueProposal,
    build_dialogue_context,
    parse_dialogue_response,
    render_dialogue_prompt,
)
from .llm_cache import LLMCallCache
from .llm_contract import PLAN_PROMPT_VERSION, build_cognition_context, parse_plan_response, render_plan_prompt
from .model import Action, Agent, Plan, WorldState
from .reflection_contract import (
    ReflectionProposal,
    build_reflection_context,
    parse_reflection_response,
    render_reflection_prompt,
)


class OpenAICognitionError(RuntimeError):
    pass


class _OpenAIResponsesProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
        base_url: str | None = None,
        reasoning_effort: str | None = None,
        cache: LLMCallCache | None = None,
        http_post: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("VIRTUAL_SOCIETY_OPENAI_API_KEY")
        )
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5.2")
        self.timeout_seconds = timeout_seconds
        self.base_url = _resolve_responses_url(
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("VIRTUAL_SOCIETY_OPENAI_BASE_URL")
        )
        self.reasoning_effort = reasoning_effort or os.environ.get("OPENAI_REASONING_EFFORT", "")
        self.cache = cache
        self.http_post = http_post
        self.prompt_version = PLAN_PROMPT_VERSION

    def _generate_text(
        self,
        surface: str,
        prompt: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> str:
        cached = self._read_cache(surface, prompt)
        if cached is not None:
            return cached
        if self.cache is not None and self.cache.mode == "read-only":
            raise OpenAICognitionError(f"LLM cache miss for {surface} in read-only mode")

        payload = {
            "model": self.model,
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        if self.reasoning_effort:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        response = self.http_post(payload) if self.http_post is not None else self._post(payload)
        text = _extract_output_text(response)
        self._write_cache(surface, prompt, text)
        return text

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=body,
            headers={
                "authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAICognitionError(f"OpenAI API request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise OpenAICognitionError(f"OpenAI API request failed: {exc}") from exc

    def _read_cache(self, surface: str, prompt: str) -> str | None:
        if self.cache is None:
            return None
        return self.cache.read(
            surface,
            self.model,
            self.reasoning_effort or "default",
            prompt,
        )

    def _write_cache(self, surface: str, prompt: str, text: str) -> None:
        if self.cache is None:
            return
        self.cache.write(
            surface,
            self.model,
            self.reasoning_effort or "default",
            prompt,
            text,
        )


class OpenAICognition(_OpenAIResponsesProvider):
    """OpenAI-compatible Responses API provider for structured agent plans."""

    def propose_plan(self, agent: Agent, world: WorldState) -> Plan:
        return self.propose_plan_with_baseline(agent, world, None)

    def propose_plan_with_baseline(
        self,
        agent: Agent,
        world: WorldState,
        baseline_plan: Plan | None,
    ) -> Plan:
        if not self.api_key and self.http_post is None:
            raise OpenAICognitionError("OPENAI_API_KEY is required for OpenAICognition")

        context = build_cognition_context(agent, world, baseline_plan=baseline_plan)
        text = self._generate_text(
            "cognition",
            render_plan_prompt(context),
            "virtual_society_plan",
            _plan_schema(),
        )
        return parse_plan_response(_loads_json_text(text))


class OpenAIReflection(_OpenAIResponsesProvider):
    """OpenAI-compatible Responses API provider for structured reflections."""

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
        if not self.api_key and self.http_post is None:
            raise OpenAICognitionError("OPENAI_API_KEY is required for OpenAIReflection")

        context = build_reflection_context(
            agent,
            world,
            current_day,
            lookback_days,
            baseline.summary,
        )
        text = self._generate_text(
            "reflection",
            render_reflection_prompt(context),
            "virtual_society_reflection",
            _reflection_schema(),
        )
        return parse_reflection_response(
            _loads_json_text(text),
            memory_count=len(context.recent_memories),
        )


class OpenAIDialogue(_OpenAIResponsesProvider):
    """OpenAI-compatible Responses API provider for structured dialogue."""

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
            DialogueProposal(text=baseline_dialogue, focus="routine"),
        )

    def propose_dialogue_with_baseline(
        self,
        speaker: Agent,
        partner: Agent,
        world: WorldState,
        baseline: DialogueProposal,
    ) -> DialogueProposal:
        if not self.api_key and self.http_post is None:
            raise OpenAICognitionError("OPENAI_API_KEY is required for OpenAIDialogue")

        context = build_dialogue_context(speaker, partner, world, baseline.text)
        text = self._generate_text(
            "dialogue",
            render_dialogue_prompt(context),
            "virtual_society_dialogue",
            _dialogue_schema(),
        )
        return parse_dialogue_response(
            _loads_json_text(text),
            memory_count=len(context.recent_memories),
        )


def _plan_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "priority", "reason", "target_id", "horizon_days"],
        "properties": {
            "action": {
                "type": "string",
                "enum": [action.value for action in Action],
            },
            "priority": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "reason": {
                "type": "string",
                "minLength": 1,
            },
            "target_id": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
            },
            "horizon_days": {
                "type": "integer",
                "minimum": 1,
            },
        },
    }


def _reflection_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "focus", "memory_refs"],
        "properties": {
            "summary": {"type": "string", "minLength": 1, "maxLength": 700},
            "focus": {
                "type": "string",
                "enum": ["shock", "social", "work", "scarcity", "identity", "routine"],
            },
            "memory_refs": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0},
            },
        },
    }


def _dialogue_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "focus", "memory_refs"],
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 1000},
            "focus": {
                "type": "string",
                "enum": ["shock", "care", "coordination", "scarcity", "relationship", "routine"],
            },
            "memory_refs": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0},
            },
        },
    }


def _resolve_responses_url(base_url: str | None) -> str:
    url = (base_url or "https://api.openai.com/v1/responses").rstrip("/")
    if url.endswith("/responses"):
        return url
    if url.endswith("/v1"):
        return f"{url}/responses"
    return f"{url}/v1/responses"


def _parse_response_text(text: str) -> Plan:
    return parse_plan_response(_loads_json_text(text))


def _loads_json_text(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenAICognitionError("OpenAI response did not contain valid JSON") from exc
    if not isinstance(parsed, dict):
        raise OpenAICognitionError("OpenAI response JSON must be an object")
    return parsed


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                return content["text"]

    raise OpenAICognitionError("OpenAI response did not contain output text")
