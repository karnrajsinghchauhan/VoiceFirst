"""Deterministic telephony test double. Records every call; can be told to fail (chaos)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.errors import ProviderError
from app.providers.base import PlacedCall


@dataclass
class MockTelephony:
    name: str = "mock"
    placed: list[tuple[str, str, str]] = field(default_factory=list)
    hung_up: list[str] = field(default_factory=list)
    fail_next: bool = False

    def place_call(self, to_e164: str, from_cli_e164: str, call_ref: str) -> PlacedCall:
        if self.fail_next:
            self.fail_next = False
            raise ProviderError("mock telephony failure")
        self.placed.append((to_e164, from_cli_e164, call_ref))
        return PlacedCall(provider_call_id=f"mock-{len(self.placed)}")

    def hang_up(self, provider_call_id: str) -> None:
        self.hung_up.append(provider_call_id)
