"""Opens a CRM case from a handoff summary. The case body is the same 5 lines the human sees live."""

from __future__ import annotations

from app.contracts.generated.handoff_summary import HandoffSummary
from app.handoff.summary import render_lines
from app.providers.base import CrmProvider, CrmTicket

# Disputes, legal threats and distress go to the front of the queue; Agoda keeps humans in charge.
_URGENT_REASONS = frozenset({"dispute", "legal", "chargeback", "fraud", "safety", "medical", "vip"})


def priority_for(summary: HandoffSummary) -> str:
    if summary.reason in _URGENT_REASONS or summary.sentiment == "distressed":
        return "urgent"
    if summary.sentiment == "angry":
        return "high"
    return "normal"


def open_case(crm: CrmProvider, summary: HandoffSummary, grievance_channel: str) -> CrmTicket:
    body = "\n".join([*render_lines(summary), f"Grievance channel: {grievance_channel}"])
    return crm.create_ticket(
        subject=f"Agoda Voice handoff: {summary.reason} ({summary.booking_masked})",
        body=body,
        requester_ref=summary.call_id,
        tags=["agoda_voice", f"reason_{summary.reason}", f"queue_{summary.queue}"],
        priority=priority_for(summary),
    )
