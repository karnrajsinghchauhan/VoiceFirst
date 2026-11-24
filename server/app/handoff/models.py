"""Tables owned by handoff/."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class HandoffRow(Base):
    __tablename__ = "handoffs"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    queue: Mapped[str] = mapped_column(String)
    result: Mapped[str] = mapped_column(String)  # transferred | callback_scheduled
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    crm_ticket_id: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)


class CallbackRow(Base):
    """A human callback promised to the customer. Dialling it still passes every gate."""

    __tablename__ = "callbacks"
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    callback_id: Mapped[str] = mapped_column(String, primary_key=True)
    call_id: Mapped[str] = mapped_column(String, index=True)
    queue: Mapped[str] = mapped_column(String)
    requested_at: Mapped[datetime] = mapped_column(UtcDateTime)
    due_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    reason: Mapped[str] = mapped_column(String)
