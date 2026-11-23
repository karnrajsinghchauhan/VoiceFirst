"""WhatsApp channel state owned by messaging/. Sends are recorded in compliance.models.WhatsAppSendRow."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class WhatsAppStateRow(Base):
    __tablename__ = "whatsapp_state"
    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    paused: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(UtcDateTime)


class InboundMessageRow(Base):
    """Last inbound message per number; opens the 24 h customer-service window (REQ-WA-03)."""

    __tablename__ = "whatsapp_inbound"
    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)
    phone_hash: Mapped[str] = mapped_column(String, primary_key=True)
    last_inbound_at: Mapped[datetime] = mapped_column(UtcDateTime)
