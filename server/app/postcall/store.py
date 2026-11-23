"""Writes and reads post-call records. Transcripts are redacted before encryption, never after."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.generated.call_outcome import CallOutcome
from app.core.bus import EventBus
from app.core.errors import NotFoundError, StateConflictError
from app.core.redaction import redact_text
from app.postcall.crypto import DataCipher
from app.postcall.models import AudioRefRow, CallOutcomeRow, TranscriptRow

Speaker = Literal["agent", "customer"]


@dataclass(frozen=True)
class TranscriptTurn:
    speaker: Speaker
    text: str


def record_outcome(session: Session, bus: EventBus, outcome: CallOutcome, phone_hash: str) -> None:
    if session.get(CallOutcomeRow, outcome.call_id) is not None:
        raise StateConflictError(f"outcome for {outcome.call_id} already recorded")
    session.add(
        CallOutcomeRow(
            call_id=outcome.call_id,
            tenant_id=outcome.tenant_id,
            trace_id=outcome.trace_id,
            booking_id=outcome.booking_id,
            phone_hash=phone_hash,
            purpose=outcome.purpose,
            outcome=outcome.outcome,
            started_at=outcome.started_at,
            payload=outcome.model_dump(mode="json"),
        )
    )
    session.flush()
    bus.publish("av.call-outcomes.v1", outcome.booking_id, outcome)


def get_outcome(session: Session, call_id: str) -> CallOutcome:
    row = session.get(CallOutcomeRow, call_id)
    if row is None:
        raise NotFoundError(f"no outcome for call {call_id}")
    return CallOutcome.model_validate(row.payload)


def list_outcomes(session: Session, limit: int) -> list[CallOutcome]:
    rows = session.scalars(
        select(CallOutcomeRow).order_by(CallOutcomeRow.started_at.desc()).limit(limit)
    )
    return [CallOutcome.model_validate(r.payload) for r in rows]


def store_transcript(
    session: Session,
    cipher: DataCipher,
    *,
    tenant_id: str,
    call_id: str,
    phone_hash: str,
    at: datetime,
    turns: list[TranscriptTurn],
) -> None:
    redacted: list[dict[str, Any]] = [
        {"speaker": t.speaker, "text": redact_text(t.text)} for t in turns
    ]
    session.add(
        TranscriptRow(
            tenant_id=tenant_id,
            call_id=call_id,
            phone_hash=phone_hash,
            created_at=at,
            ciphertext=cipher.encrypt_json(redacted),
        )
    )
    session.flush()


def read_transcript(session: Session, cipher: DataCipher, call_id: str) -> list[TranscriptTurn]:
    row = session.get(TranscriptRow, call_id)
    if row is None:
        raise NotFoundError(f"no transcript for call {call_id}")
    return [
        TranscriptTurn(speaker=t["speaker"], text=t["text"])
        for t in cipher.decrypt_json(row.ciphertext)
    ]


def store_audio_ref(
    session: Session,
    cipher: DataCipher,
    *,
    tenant_id: str,
    call_id: str,
    phone_hash: str,
    at: datetime,
    uri: str,
) -> None:
    session.add(
        AudioRefRow(
            tenant_id=tenant_id,
            call_id=call_id,
            phone_hash=phone_hash,
            created_at=at,
            ciphertext=cipher.encrypt_json({"uri": uri}),
        )
    )
    session.flush()
