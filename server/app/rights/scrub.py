"""Removes personal fields that outlive the call: booking-event payloads, clearances and
handoff summaries (review R2 H1). One owner, used by erasure and by the nightly purge.

Consent and opt-out records are kept on purpose (D-302): they prove the lawful basis and
stop the number being called again.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.campaigns.models import BookingEventRow, QueueItemRow
from app.compliance.models import ClearanceRow, DialAttemptRow
from app.handoff.models import HandoffRow

ERASED = "erased"


@dataclass(frozen=True)
class ScrubCounts:
    booking_events: int
    clearances: int
    handoffs: int


def _scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    customer = {**payload["customer"], "phone_e164": ERASED, "first_name": ERASED}
    return {**payload, "customer": customer}


def _scrub_handoff(row: HandoffRow) -> None:
    row.summary = {**row.summary, "who": ERASED}


def erase_for_phone(
    session: Session, phone_e164: str, phone_hash: str, at: datetime
) -> ScrubCounts:
    events = [
        e
        for e in session.scalars(select(BookingEventRow))
        if e.payload["customer"]["phone_e164"] == phone_e164
    ]
    for e in events:
        e.payload = _scrub_payload(e.payload)
    if events:
        # An erased booking can no longer be dialled; queued work for it is dropped, not failed.
        session.execute(
            update(QueueItemRow)
            .where(
                QueueItemRow.booking_event_id.in_([e.event_id for e in events]),
                QueueItemRow.state == "queued",
            )
            .values(state="dropped", last_reason="erased", updated_at=at)
        )
    clearances = session.execute(
        update(ClearanceRow).where(ClearanceRow.phone_e164 == phone_e164).values(phone_e164=ERASED)
    ).rowcount
    call_ids = select(DialAttemptRow.call_id).where(DialAttemptRow.phone_hash == phone_hash)
    handoffs = list(session.scalars(select(HandoffRow).where(HandoffRow.call_id.in_(call_ids))))
    for h in handoffs:
        _scrub_handoff(h)
    session.flush()
    return ScrubCounts(booking_events=len(events), clearances=clearances, handoffs=len(handoffs))


def scrub_older_than(session: Session, cutoff: datetime) -> ScrubCounts:
    events = [
        e
        for e in session.scalars(
            select(BookingEventRow).where(BookingEventRow.received_at < cutoff)
        )
        if e.payload["customer"]["phone_e164"] != ERASED
    ]
    for e in events:
        e.payload = _scrub_payload(e.payload)
    clearances = session.execute(
        update(ClearanceRow)
        .where(ClearanceRow.issued_at < cutoff, ClearanceRow.phone_e164 != ERASED)
        .values(phone_e164=ERASED)
    ).rowcount
    handoffs = [
        h
        for h in session.scalars(select(HandoffRow).where(HandoffRow.created_at < cutoff))
        if h.summary.get("who") != ERASED
    ]
    for h in handoffs:
        _scrub_handoff(h)
    session.flush()
    return ScrubCounts(booking_events=len(events), clearances=clearances, handoffs=len(handoffs))
