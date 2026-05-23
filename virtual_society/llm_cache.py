from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class LLMCacheRecord:
    schema_version: int
    key: str
    surface: str
    provider: str
    model: str
    reasoning_effort: str
    prompt_sha256: str
    prompt: str
    response: str
    created_at: str


@dataclass
class LLMCacheStats:
    reads: int = 0
    hits: int = 0
    misses: int = 0
    writes: int = 0


class LLMCallCache:
    """Disk cache for raw LLM prompt/response pairs."""

    def __init__(
        self,
        root_dir: str | Path,
        mode: str = "read-write",
        provider: str = "codex-cli",
    ) -> None:
        if mode not in {"read-write", "read-only", "refresh"}:
            raise ValueError("cache mode must be read-write, read-only, or refresh")
        self.root_dir = Path(root_dir)
        self.mode = mode
        self.provider = provider
        self.stats = LLMCacheStats()

    def read(
        self,
        surface: str,
        model: str,
        reasoning_effort: str,
        prompt: str,
    ) -> str | None:
        if self.mode == "refresh":
            self.stats.misses += 1
            return None

        self.stats.reads += 1
        path = self.path_for(surface, model, reasoning_effort, prompt)
        if not path.exists():
            self.stats.misses += 1
            return None

        record = json.loads(path.read_text(encoding="utf-8"))
        response = str(record.get("response", ""))
        self.stats.hits += 1
        return response

    def write(
        self,
        surface: str,
        model: str,
        reasoning_effort: str,
        prompt: str,
        response: str,
    ) -> Path:
        if self.mode == "read-only":
            raise ValueError("cannot write LLM cache in read-only mode")

        path = self.path_for(surface, model, reasoning_effort, prompt)
        path.parent.mkdir(parents=True, exist_ok=True)
        key = self.key_for(surface, model, reasoning_effort, prompt)
        record = LLMCacheRecord(
            schema_version=CACHE_SCHEMA_VERSION,
            key=key,
            surface=surface,
            provider=self.provider,
            model=model,
            reasoning_effort=reasoning_effort,
            prompt_sha256=_sha256(prompt),
            prompt=prompt,
            response=response,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        path.write_text(
            json.dumps(asdict(record), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.stats.writes += 1
        return path

    def path_for(
        self,
        surface: str,
        model: str,
        reasoning_effort: str,
        prompt: str,
    ) -> Path:
        key = self.key_for(surface, model, reasoning_effort, prompt)
        return self.root_dir / _safe_part(surface) / f"{key}.json"

    def key_for(
        self,
        surface: str,
        model: str,
        reasoning_effort: str,
        prompt: str,
    ) -> str:
        payload: dict[str, Any] = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "provider": self.provider,
            "surface": surface,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "prompt": prompt,
        }
        return _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_part(value: str) -> str:
    return "".join(
        character
        if character.isalnum() or character in {"-", "_"}
        else "_"
        for character in value
    )
