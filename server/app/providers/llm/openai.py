"""OpenAI chat-completions adapter. Thin httpx client; never called in tests (no keys, D-007).

The request/response shape follows the public Chat Completions API; it has not
been exercised this session and must be checked on the first real call.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.providers.base import ChatMessage, LlmTurn, ToolCall, ToolSpec

_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class OpenAiLlm:
    api_key: str
    model_id: str
    timeout_s: float = 3.0
    name: str = "openai"

    @classmethod
    def from_env(cls) -> OpenAiLlm:
        key, model = os.environ.get("OPENAI_API_KEY"), os.environ.get("AV_OPENAI_MODEL")
        if not key or not model:
            raise ConfigError("OPENAI_API_KEY and AV_OPENAI_MODEL must be set for llm=openai")
        return cls(key, model)

    def next_turn(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LlmTurn:
        body = {
            "model": self.model_id,
            "temperature": 0,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": {
                            "type": "object",
                            "properties": {p: {"type": "string"} for p in t.params},
                            "required": list(t.params),
                        },
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
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("openai timed out") from exc
        if resp.status_code != 200:
            raise ProviderError(f"openai returned {resp.status_code}")
        message = resp.json()["choices"][0]["message"]
        calls = tuple(
            ToolCall(c["function"]["name"], json.loads(c["function"]["arguments"] or "{}"))
            for c in message.get("tool_calls") or []
        )
        return LlmTurn(utterance=message.get("content") or "", tool_calls=calls)
