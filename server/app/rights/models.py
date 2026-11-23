"""Tables owned by rights/."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime

RightsKind = Literal["access", "correction", "erasure"]
RightsStatus = Literal["open", "acknowledged", "completed"]


class RightsRequestRow(Base):
    __tablename__ = "rights_requests"
    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[RightsKind] = mapped_column(String)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime)
    ack_due_at: Mapped[datetime] = mapped_column(UtcDateTime)
    due_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    status: Mapped[RightsStatus] = mapped_column(String)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
