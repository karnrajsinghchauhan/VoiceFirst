"""Test doubles for the dispatcher's two ports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.call_outcome import CallOutcome
from app.core.clock import Clock
from app.core.errors import FallbackCapError
from app.telephony.handle import CallHandle

OutcomeName = Literal["link_sent", "details_confirmed", "no_answer", "handed_off"]


def make_outcome(
    handle: CallHandle, event: BookingEvent, outcome: str, clock: Clock
) -> CallOutcome:
    zero = "0" * 64
    return CallOutcome.model_validate(
        {
            "schema_version": "1.0.0",
            "tenant_id": event.tenant_id,
            "trace_id": event.trace_id,
            "call_id": handle.call_id,
            "clearance_id": handle.clearance.clearance_id,
            "booking_id": event.booking_id,
            "purpose": handle.clearance.purpose,
            "cli": handle.clearance.cli_e164,
            "started_at": clock.now().isoformat(),
            "answered": outcome != "no_answer",
            "amd_result": "human",
            "language_detected": "hinglish",
            "disclosure_played_at": None if outcome == "no_answer" else clock.now().isoformat(),
            "turns": 0 if outcome == "no_answer" else 6,
            "tools_called": [],
            "outcome": outcome,
            "handoff": None,
            "latency_ms": {"p50": 600, "p95": 1100},
            "cost": {"telephony": 76, "stt": 98, "tts": 120, "llm": 40, "whatsapp": 0},
            "redaction_applied": True,
            "sensitive_data_spoken": False,
            "grievance_channel": "grievance",
            "ai_generated": True,
            "model_ids": {"llm": "mock"},
            "provenance_hash": zero,
        }
    )


@dataclass
class StubRunner:
    """Outcome is a pure function of (booking_id, attempt): about 30% no-answer per attempt."""

    clock: Clock
    calls: list[tuple[str, str]] = field(default_factory=list)

    def run(
        self, handle: CallHandle, event: BookingEvent, purpose: Literal["J1", "J2"]
    ) -> CallOutcome:
        attempt = sum(1 for b, _ in self.calls if b == event.booking_id) + 1
        self.calls.append((event.booking_id, handle.call_id))
        roll = int(hashlib.sha256(f"{event.booking_id}:{attempt}".encode()).hexdigest(), 16) % 10
        if roll < 3:
            name = "no_answer"
        elif roll < 4:
            name = "handed_off"
        else:
            name = "link_sent" if purpose == "J1" else "details_confirmed"
        return make_outcome(handle, event, name, self.clock)


@dataclass
class FixedRunner:
    clock: Clock
    outcome: str
    calls: list[str] = field(default_factory=list)

    def run(
        self, handle: CallHandle, event: BookingEvent, purpose: Literal["J1", "J2"]
    ) -> CallOutcome:
        self.calls.append(handle.call_id)
        return make_outcome(handle, event, self.outcome, self.clock)


@dataclass
class RecordingFallback:
    """Mirrors the messaging module's contract: at most one fallback per event."""

    sent: list[str] = field(default_factory=list)

    def send_no_answer_fallback(self, event: BookingEvent) -> None:
        if event.event_id in self.sent:
            raise FallbackCapError("fallback already sent for this event")
        self.sent.append(event.event_id)
