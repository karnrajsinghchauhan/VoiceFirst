"""The agent's tool allowlist (P1) and the ToolBackend port for side effects.

No tool can refund, cancel, re-price, issue Agoda Cash or waive anything. Any
name outside ALLOWED_TOOLS raises ToolNotAllowedError. The agent reaches the
outside world only through ToolBackend; the lead wires the real backend
(messaging, compliance.consent.mark_dnc, handoff, CRM). RecordingToolBackend is
the in-memory double used by tests, evals and the demo.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.call_outcome import ToolsCalledItem
from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.errors import ProviderError, ToolNotAllowedError
from app.core.ids import sha256_hex
from app.providers.base import ToolSpec

ToolName = Literal[
    "get_booking_summary",
    "send_payment_link",
    "confirm_details",
    "record_special_request",
    "log_case",
    "schedule_callback",
    "warm_transfer",
    "mark_dnc",
    "end_call",
    "send_app_link",
]

TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("get_booking_summary", "Read the purpose-limited booking facts.", ()),
    ToolSpec(
        "send_payment_link", "Send the Agoda-hosted payment link by WhatsApp utility template.", ()
    ),
    ToolSpec("confirm_details", "Record that the customer confirmed stay details.", ("details",)),
    ToolSpec(
        "record_special_request",
        "Record a special request or arrival time for the property.",
        ("text",),
    ),
    ToolSpec("log_case", "Open a case for a human team.", ("category", "summary")),
    ToolSpec("schedule_callback", "Schedule a human or booker callback.", ("reason", "when")),
    ToolSpec("warm_transfer", "Transfer to a human with a summary.", ("reason", "queue")),
    ToolSpec("mark_dnc", "Opt the number out of calls.", ()),
    ToolSpec("end_call", "End the call.", ("outcome",)),
    ToolSpec(
        "send_app_link", "Send the Agoda app link by WhatsApp; customer-initiated only (D-001).", ()
    ),
)
ALLOWED_TOOLS: frozenset[str] = frozenset(spec.name for spec in TOOL_SPECS)


@dataclass(frozen=True)
class ToolResult:
    code: str
    ref: str | None = None
    cost_paise: int = 0


@dataclass(frozen=True)
class TransferResult:
    connected: bool
    queue: str
    ref: str | None = None


class ToolBackend(Protocol):
    """Side effects of the allowlisted tools. Each method raises an AgodaVoiceError on failure."""

    def send_payment_link(self, call_id: str, event: BookingEvent) -> ToolResult: ...

    def send_app_link(self, call_id: str, event: BookingEvent) -> ToolResult: ...

    def confirm_details(
        self, call_id: str, event: BookingEvent, details: dict[str, str]
    ) -> ToolResult: ...

    def record_special_request(
        self, call_id: str, event: BookingEvent, text: str
    ) -> ToolResult: ...

    def log_case(
        self, call_id: str, event: BookingEvent, category: str, summary: str
    ) -> ToolResult: ...

    def schedule_callback(
        self, call_id: str, event: BookingEvent, reason: str, when: str
    ) -> ToolResult: ...

    def warm_transfer(
        self, call_id: str, event: BookingEvent, summary: HandoffSummary
    ) -> TransferResult: ...

    def mark_dnc(self, call_id: str, event: BookingEvent) -> ToolResult: ...

    def end_call(self, call_id: str, outcome: str) -> ToolResult: ...

    def alert(self, call_id: str, code: str, detail: str) -> None:
        """Pages operations; not a tool the agent can choose."""
        ...


@dataclass
class RecordingToolBackend:
    """In-memory backend. `humans_available=False` models an empty queue (P2 'never pretends')."""

    humans_available: bool = True
    latency_s: dict[str, float] = field(default_factory=dict)
    fail_tools: frozenset[str] = frozenset()
    advance: Callable[[float], None] | None = None
    calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    alerts: list[tuple[str, str]] = field(default_factory=list)
    summaries: list[HandoffSummary] = field(default_factory=list)

    def _record(self, name: str, **args: object) -> None:
        if self.advance is not None:
            self.advance(self.latency_s.get(name, 0.05))
        if name in self.fail_tools:
            raise ProviderError(f"{name} backend failure")
        self.calls.append((name, args))

    def send_payment_link(self, call_id: str, event: BookingEvent) -> ToolResult:
        self._record("send_payment_link", booking_id=event.booking_id)
        return ToolResult("sent", f"wamid-{len(self.calls)}", cost_paise=14)

    def send_app_link(self, call_id: str, event: BookingEvent) -> ToolResult:
        self._record(
            "send_app_link", booking_id=event.booking_id, log="customer_initiated_offer_request"
        )
        return ToolResult("sent", f"wamid-{len(self.calls)}", cost_paise=14)

    def confirm_details(
        self, call_id: str, event: BookingEvent, details: dict[str, str]
    ) -> ToolResult:
        self._record("confirm_details", **details)
        return ToolResult("confirmed")

    def record_special_request(self, call_id: str, event: BookingEvent, text: str) -> ToolResult:
        self._record("record_special_request", text=text)
        return ToolResult("recorded")

    def log_case(
        self, call_id: str, event: BookingEvent, category: str, summary: str
    ) -> ToolResult:
        self._record("log_case", category=category, summary=summary)
        return ToolResult("logged", f"case-{len(self.calls)}")

    def schedule_callback(
        self, call_id: str, event: BookingEvent, reason: str, when: str
    ) -> ToolResult:
        self._record("schedule_callback", reason=reason, when=when)
        return ToolResult("scheduled", f"cb-{len(self.calls)}")

    def warm_transfer(
        self, call_id: str, event: BookingEvent, summary: HandoffSummary
    ) -> TransferResult:
        self._record("warm_transfer", reason=summary.reason, queue=summary.queue)
        self.summaries.append(summary)
        return TransferResult(self.humans_available, summary.queue, f"xfer-{len(self.calls)}")

    def mark_dnc(self, call_id: str, event: BookingEvent) -> ToolResult:
        self._record("mark_dnc")
        return ToolResult("dnc_marked")

    def end_call(self, call_id: str, outcome: str) -> ToolResult:
        self._record("end_call", outcome=outcome)
        return ToolResult("ended")

    def alert(self, call_id: str, code: str, detail: str) -> None:
        self.alerts.append((code, detail))

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def args_hash(name: str, args: dict[str, object]) -> str:
    return sha256_hex(json.dumps({"tool": name, "args": args}, sort_keys=True, default=str))


def check_allowed(name: str) -> None:
    if name not in ALLOWED_TOOLS:
        raise ToolNotAllowedError(f"tool {name!r} is not on the allowlist")


def ledger_entry(name: str, args: dict[str, object], result_code: str) -> ToolsCalledItem:
    check_allowed(name)
    return ToolsCalledItem(name=name, args_hash=args_hash(name, args), result_code=result_code)
