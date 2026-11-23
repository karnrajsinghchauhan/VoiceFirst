"""One row per accepted inbound webhook delivery; the primary key is the replay guard."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime

WebhookSource = Literal["whatsapp", "telephony"]


class WebhookReceiptRow(Base):
    __tablename__ = "webhook_receipts"
    source: Mapped[WebhookSource] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)  # message | status | <livekit event name>
    detail: Mapped[str] = mapped_column(String)  # status value or event summary, never content
    sent_at: Mapped[datetime] = mapped_column(UtcDateTime)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
