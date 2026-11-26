"""One interface per provider role (7.7). Implementations live in providers/<role>/<name>.py.

Every implementation raises ProviderError (or a subclass) on failure. No caller
catches a ProviderError in order to try another provider (rule 6.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.core.types import Language


@dataclass(frozen=True)
class Transcript:
    text: str
    language: Language
    confidence: float


class SttProvider(Protocol):
    name: str
    model_id: str

    def transcribe(self, pcm16_8khz: bytes, language_hint: Language) -> Transcript: ...


class TtsProvider(Protocol):
    name: str
    model_id: str
    voice_id: str
    voice_gender: Literal["female", "male"]

    def synthesize(self, text: str, language: Language) -> bytes:
        """Returns 16-bit PCM at 8 kHz mono."""
        ...


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, str]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "assistant", "user", "tool"]
    content: str


@dataclass(frozen=True)
class LlmTurn:
    utterance: str
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: tuple[str, ...]


class LlmProvider(Protocol):
    name: str
    model_id: str

    def next_turn(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LlmTurn: ...


@dataclass(frozen=True)
class PlacedCall:
    provider_call_id: str


class TelephonyProvider(Protocol):
    """Only telephony.dial may call place_call (import-linter enforces the caller)."""

    name: str

    def place_call(self, to_e164: str, from_cli_e164: str, call_ref: str) -> PlacedCall: ...

    def hang_up(self, provider_call_id: str) -> None: ...


@dataclass(frozen=True)
class SentMessage:
    provider_message_id: str


class WhatsAppProvider(Protocol):
    name: str

    def send_template(
        self, to_e164: str, template: str, language: Language, params: dict[str, str]
    ) -> SentMessage: ...

    def send_text(self, to_e164: str, text: str) -> SentMessage: ...

    def quality_rating(self) -> Literal["high", "medium", "low"]: ...


@dataclass(frozen=True)
class CrmTicket:
    ticket_id: str
    url: str


class CrmProvider(Protocol):
    name: str

    def create_ticket(
        self, subject: str, body: str, requester_ref: str, tags: list[str], priority: str
    ) -> CrmTicket: ...

    def add_note(self, ticket_id: str, body: str) -> None: ...
