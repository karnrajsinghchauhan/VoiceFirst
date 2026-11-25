"""Tables owned by campaigns/: received booking events, the dial queue, holdout membership."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime

QueueState = Literal[
    "queued",  # waiting for due_at
    "in_call",  # dialled; the call runner has not reported an outcome yet
    "held_out",  # in the J3 holdout; never dialled
    "blocked",  # a non-retryable gate failed
    "dropped",  # kill switch or a newer booking event made it moot
    "done",  # the journey reached a final outcome
    "error",  # a provider failed at dial time; the error was raised to the caller
]


class BookingEventRow(Base):
    __tablename__ = "booking_events"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    booking_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class QueueItemRow(Base):
    """One journey for one booking event. Up to max_attempts_per_event dials are made from one item."""

    __tablename__ = "dial_queue"
    item_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    booking_event_id: Mapped[str] = mapped_column(String, index=True)
    booking_id: Mapped[str] = mapped_column(String, index=True)
    purpose: Mapped[Literal["J1", "J2"]] = mapped_column(String)
    cli_e164: Mapped[str] = mapped_column(String)
    due_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    state: Mapped[QueueState] = mapped_column(String, index=True)
    attempts: Mapped[int] = mapped_column(Integer)
    last_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    last_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    last_dialled_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)


class HoldoutMemberRow(Base):
    """Bookings deliberately not called; the control group for lift (J3)."""

    __tablename__ = "holdout_members"
    booking_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    booking_event_id: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String)
    experiment_salt: Mapped[str] = mapped_column(String)
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime)
