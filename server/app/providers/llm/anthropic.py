"""Anthropic Messages API adapter. Thin httpx client; never called in tests (no keys, D-007).

System and STATE messages go into the `system` field; consecutive same-role
turns are merged because the API requires alternating roles. Shape follows the
public Messages API and must be checked on the first real call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.providers.base import ChatMessage, LlmTurn, ToolCall, ToolSpec

_URL = "https://api.anthropic.com/v1/messages"


@dataclass
class AnthropicLlm:
    api_key: str
    model_id: str
    timeout_s: float = 3.0
    name: str = "anthropic"

    @classmethod
    def from_env(cls) -> AnthropicLlm:
        key, model = os.environ.get("ANTHROPIC_API_KEY"), os.environ.get("AV_ANTHROPIC_MODEL")
        if not key or not model:
            raise ConfigError(
                "ANTHROPIC_API_KEY and AV_ANTHROPIC_MODEL must be set for llm=anthropic"
            )
        return cls(key, model)

    def next_turn(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LlmTurn:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        turns: list[dict[str, str]] = []
        for m in messages:
            if m.role == "system":
                continue
            role = "assistant" if m.role == "assistant" else "user"
            if turns and turns[-1]["role"] == role:
                turns[-1]["content"] += "\n" + m.content
            else:
                turns.append({"role": role, "content": m.content})
        if not turns or turns[0]["role"] != "user":
            turns.insert(0, {"role": "user", "content": "(call connected)"})
        body = {
            "model": self.model_id,
            "max_tokens": 300,
            "temperature": 0,
            "system": system,
            "messages": turns,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": {
                        "type": "object",
                        "properties": {p: {"type": "string"} for p in t.params},
                        "required": list(t.params),
                    },
                }
                for t in tools
            ],
        }
        try:
            resp = httpx.post(
                _URL,
                json=body,
                timeout=self.timeout_s,
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("anthropic timed out") from exc
        if resp.status_code != 200:
            raise ProviderError(f"anthropic returned {resp.status_code}")
        blocks = resp.json()["content"]
        text = " ".join(b["text"] for b in blocks if b["type"] == "text").strip()
        calls = tuple(
            ToolCall(b["name"], {k: str(v) for k, v in b["input"].items()})
            for b in blocks
            if b["type"] == "tool_use"
        )
        return LlmTurn(utterance=text, tool_calls=calls)
