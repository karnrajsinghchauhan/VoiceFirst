"""Deterministic WhatsApp test double."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.core.errors import ProviderError
from app.core.types import Language
from app.providers.base import SentMessage


@dataclass
class MockWhatsApp:
    name: str = "mock"
    sent: list[dict[str, object]] = field(default_factory=list)
    rating: Literal["high", "medium", "low"] = "high"
    fail_next: bool = False

    def send_template(
        self, to_e164: str, template: str, language: Language, params: dict[str, str]
    ) -> SentMessage:
        if self.fail_next:
            self.fail_next = False
            raise ProviderError("mock whatsapp failure")
        self.sent.append(
            {"to": to_e164, "template": template, "language": language, "params": dict(params)}
        )
        return SentMessage(provider_message_id=f"wamid-{len(self.sent)}")

    def send_text(self, to_e164: str, text: str) -> SentMessage:
        self.sent.append({"to": to_e164, "text": text})
        return SentMessage(provider_message_id=f"wamid-{len(self.sent)}")

    def quality_rating(self) -> Literal["high", "medium", "low"]:
        return self.rating
