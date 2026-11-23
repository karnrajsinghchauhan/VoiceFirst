"""Deterministic mock LLM. It phrases the acts the conversation engine chose (D-009):
it renders each act from the versioned lines and returns exactly the requested tool calls.
No network; seeded latency on a SimTimer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.core.errors import ProviderError, ProviderTimeoutError
from app.providers.base import ChatMessage, LlmTurn, ToolCall, ToolSpec
from app.providers.latency import LatencyModel, SimTimer
from app.voice.prompts import render

STATE_PREFIX = "STATE "


@dataclass
class MockLlm:
    timer: SimTimer
    latency: LatencyModel
    name: str = "mock"
    model_id: str = "mock-policy-v1"
    fail_after_calls: int | None = None
    slow_s: float = 0.0
    calls: int = field(default=0)

    def next_turn(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LlmTurn:
        self.calls += 1
        if self.fail_after_calls is not None and self.calls > self.fail_after_calls:
            raise ProviderError("mock LLM unavailable")
        elapsed = self.latency.sample() + self.slow_s
        self.timer.advance(elapsed)
        if self.slow_s:
            raise ProviderTimeoutError(f"mock LLM exceeded its deadline after {elapsed:.1f}s")
        state = json.loads(messages[-1].content.removeprefix(STATE_PREFIX))
        values = {k: str(v) for k, v in state["values"].items()}
        utterance = " ".join(render(act, state["language"], values) for act in state["acts"])
        calls = tuple(ToolCall(t["name"], dict(t["args"])) for t in state["tools"])
        return LlmTurn(utterance=utterance, tool_calls=calls)
