"""Tables owned by postcall/: outcomes, encrypted redacted transcripts, encrypted audio references."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class CallOutcomeRow(Base):
    __tablename__ = "call_outcomes"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    trace_id: Mapped[str] = mapped_column(String)
    booking_id: Mapped[str] = mapped_column(String, index=True)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    purpose: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class TranscriptRow(Base):
    __tablename__ = "transcripts"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class AudioRefRow(Base):
    __tablename__ = "audio_refs"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    phone_hash: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
