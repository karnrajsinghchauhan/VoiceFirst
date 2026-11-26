"""Warm transfer (P2). A human is always one sentence away; if none is free we say so and book a callback.

The agent never pretends a transfer happened: the spoken line is chosen from
the queue's real answer, not from what the customer hoped for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.errors import NotFoundError, StateConflictError
from app.core.ids import new_id
from app.handoff.models import CallbackRow, HandoffRow

VoiceGender = Literal["female", "male"]
TransferKind = Literal["transferred", "callback_scheduled"]

CALLBACK_DELAY = timedelta(hours=2)


class HumanQueue(Protocol):
    """The contact-centre side (Agoda's CCaaS in production)."""

    def has_available_agent(self, queue: str) -> bool: ...

    def connect(self, queue: str, summary: HandoffSummary) -> str:
        """Bridges the live call to a human and returns the agent reference."""
        ...


@dataclass
class InMemoryHumanQueue:
    """Deterministic test double."""

    available: dict[str, int] = field(default_factory=dict)
    connected: list[tuple[str, str]] = field(default_factory=list)

    def has_available_agent(self, queue: str) -> bool:
        return self.available.get(queue, 0) > 0

    def connect(self, queue: str, summary: HandoffSummary) -> str:
        if not self.has_available_agent(queue):
            raise StateConflictError(f"no agent free on {queue}")
        self.available[queue] -= 1
        self.connected.append((queue, summary.call_id))
        return f"agent-{queue}-{len(self.connected)}"


@dataclass(frozen=True)
class TransferResult:
    kind: TransferKind
    spoken_line: str
    agent_ref: str | None
    callback_due_at: datetime | None


def _lines(gender: VoiceGender) -> dict[TransferKind, str]:
    verb = "rahi" if gender == "female" else "raha"
    return {
        "transferred": (
            f"Ek minute ji, main aapko hamari team se jod {verb} hoon — "
            "unhe poori baat bata di hai."
        ),
        "callback_scheduled": (
            "Is samay hamari team ka koi saathi uplabdh nahi hai. "
            f"Main aapke liye callback schedule kar {verb} hoon, team aapko jald call karegi."
        ),
    }


def warm_transfer(
    session: Session,
    bus: EventBus,
    queue: HumanQueue,
    clock: Clock,
    summary: HandoffSummary,
    gender: VoiceGender,
) -> TransferResult:
    now = clock.now()
    if session.get(HandoffRow, summary.call_id) is not None:
        raise StateConflictError(f"call {summary.call_id} already handed off")
    lines = _lines(gender)
    if queue.has_available_agent(summary.queue):
        agent_ref = queue.connect(summary.queue, summary)
        result = TransferResult("transferred", lines["transferred"], agent_ref, None)
    else:
        due = now + CALLBACK_DELAY
        session.add(
            CallbackRow(
                callback_id=new_id("cb"),
                tenant_id=summary.tenant_id,
                call_id=summary.call_id,
                queue=summary.queue,
                requested_at=now,
                due_at=due,
                reason=summary.reason,
            )
        )
        result = TransferResult("callback_scheduled", lines["callback_scheduled"], None, due)
    session.add(
        HandoffRow(
            call_id=summary.call_id,
            tenant_id=summary.tenant_id,
            queue=summary.queue,
            result=result.kind,
            created_at=now,
            acknowledged_at=None,
            resolved_at=None,
            crm_ticket_id=None,
            summary=summary.model_dump(mode="json"),
        )
    )
    session.flush()
    bus.publish("av.handoffs.v1", summary.call_id, summary)
    return result


def attach_ticket(session: Session, call_id: str, ticket_id: str) -> None:
    row = _get(session, call_id)
    row.crm_ticket_id = ticket_id
    session.flush()


def acknowledge(session: Session, call_id: str, at: datetime) -> None:
    row = _get(session, call_id)
    if row.acknowledged_at is not None:
        raise StateConflictError(f"handoff {call_id} already acknowledged")
    row.acknowledged_at = at
    session.flush()


def resolve(session: Session, call_id: str, at: datetime) -> None:
    row = _get(session, call_id)
    if row.resolved_at is not None:
        raise StateConflictError(f"handoff {call_id} already resolved")
    row.resolved_at = at
    session.flush()


def _get(session: Session, call_id: str) -> HandoffRow:
    row = session.get(HandoffRow, call_id)
    if row is None:
        raise NotFoundError(f"no handoff for call {call_id}")
    return row


def get_summary(session: Session, call_id: str) -> HandoffSummary:
    return HandoffSummary.model_validate(_get(session, call_id).summary)


def list_open(session: Session, limit: int) -> list[HandoffRow]:
    stmt = (
        select(HandoffRow)
        .where(HandoffRow.resolved_at.is_(None))
        .order_by(HandoffRow.created_at)
        .limit(limit)
    )
    return list(session.scalars(stmt))


@dataclass(frozen=True)
class SlaBreaches:
    unacknowledged: list[str]
    unresolved: list[str]


def sla_breaches(session: Session, now: datetime) -> SlaBreaches:
    """Cases past their 48 h acknowledgement or 30-day resolution deadline (REQ-CP-03)."""
    unack: list[str] = []
    unres: list[str] = []
    for row in session.scalars(select(HandoffRow).where(HandoffRow.resolved_at.is_(None))):
        summary = HandoffSummary.model_validate(row.summary)
        if row.acknowledged_at is None and now >= summary.sla_ack_due_at:
            unack.append(row.call_id)
        if now >= summary.sla_resolve_due_at:
            unres.append(row.call_id)
    return SlaBreaches(unacknowledged=unack, unresolved=unres)
