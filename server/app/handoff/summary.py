"""HandoffSummary builder (8.6). Shaped like Agoda's own case summary: at most 5 lines a human can scan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.ids import mask_booking_id

Sentiment = Literal["calm", "concerned", "angry", "distressed"]

# REQ-CP-03: mirrors the E-Commerce Rules acknowledgement and resolution timelines.
ACK_SLA = timedelta(hours=48)
RESOLVE_SLA = timedelta(days=30)
MAX_LINES = 5


@dataclass(frozen=True)
class HandoffFacts:
    """What the call runner knows at the moment of transfer."""

    tenant_id: str
    trace_id: str
    call_id: str
    first_name: str
    purpose: str
    booking_id: str
    customer_wants: str
    ai_did: str
    sentiment: Sentiment
    policy_refs: tuple[str, ...]
    next_best_action: str
    reason: str
    queue: str
    at: datetime


def build_summary(facts: HandoffFacts) -> HandoffSummary:
    return HandoffSummary(
        schema_version="1.0.0",
        tenant_id=facts.tenant_id,
        trace_id=facts.trace_id,
        call_id=facts.call_id,
        who=f"{facts.first_name} ({facts.purpose} call)",
        booking_masked=mask_booking_id(facts.booking_id),
        customer_wants=facts.customer_wants,
        ai_did=facts.ai_did,
        sentiment=facts.sentiment,
        policy_refs=list(facts.policy_refs),
        next_best_action=facts.next_best_action,
        reason=facts.reason,
        queue=facts.queue,
        sla_ack_due_at=facts.at + ACK_SLA,
        sla_resolve_due_at=facts.at + RESOLVE_SLA,
    )


def render_lines(summary: HandoffSummary) -> list[str]:
    """The human-facing text. Exactly MAX_LINES lines, each one fact family."""
    policies = ", ".join(summary.policy_refs) if summary.policy_refs else "none"
    return [
        f"Who: {summary.who}; booking {summary.booking_masked}",
        f"Wants: {summary.customer_wants}",
        f"AI did: {summary.ai_did}",
        f"Sentiment: {summary.sentiment}; reason: {summary.reason}; policy: {policies}",
        f"Next: {summary.next_best_action}",
    ]
