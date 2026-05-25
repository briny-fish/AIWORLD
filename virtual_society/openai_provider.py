from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .llm_contract import PLAN_PROMPT_VERSION, build_cognition_context, parse_plan_response, render_plan_prompt
from .model import Action, Agent, Plan, WorldState


class OpenAICognitionError(RuntimeError):
    pass


class OpenAICognition:
    """OpenAI Responses API provider for structured agent plans."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
        base_url: str = "https://api.openai.com/v1/responses",
        http_post: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5.2")
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url
        self.http_post = http_post
        self.prompt_version = PLAN_PROMPT_VERSION

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
        prompt = render_plan_prompt(context)
        payload = {
            "model": self.model,
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "virtual_society_plan",
                    "strict": True,
                    "schema": _plan_schema(),
                }
            },
        }
        response = self.http_post(payload) if self.http_post is not None else self._post(payload)
        text = _extract_output_text(response)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenAICognitionError("OpenAI response did not contain valid JSON") from exc
        return parse_plan_response(data)

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


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                return content["text"]

    raise OpenAICognitionError("OpenAI response did not contain output text")
