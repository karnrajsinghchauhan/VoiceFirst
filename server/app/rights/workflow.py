"""DPDP rights requests: access, correction, erasure, each with SLA timers (REQ-DPDP-05).

Erasure removes transcripts and audio, and pseudonymises call outcomes so lift
analytics still count. Consent and opt-out records are kept: they prove the
lawful basis of past calls and are what keeps an opted-out number from being
called again. Their legal retention period is [CD] (docs/discovery-questions.md 15).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.compliance.consent import consents_for
from app.core.audit import Role, write_audit
from app.core.bus import EventBus
from app.core.config import Settings
from app.core.errors import NotFoundError, StateConflictError
from app.core.ids import new_id, phone_hash, sha256_hex
from app.postcall.crypto import DataCipher
from app.postcall.models import AudioRefRow, CallOutcomeRow, TranscriptRow
from app.rights.models import RightsKind, RightsRequestRow

ERASED = "erased"


class RightsSlaSettings(BaseSettings):
    """[CD] statutory timelines; house defaults until counsel confirms."""

    model_config = SettingsConfigDict(env_prefix="AV_RIGHTS_", extra="ignore", frozen=True)

    ack_hours: int = 48
    resolve_days: int = 30


@dataclass(frozen=True)
class Actor:
    actor: str
    role: Role


def _audit(
    session: Session,
    bus: EventBus,
    settings: Settings,
    row: RightsRequestRow,
    actor: Actor,
    action: str,
    at: datetime,
) -> None:
    write_audit(
        session,
        bus,
        tenant_id=settings.tenant_id,
        trace_id=sha256_hex(row.request_id)[:32],
        at=at,
        actor=actor.actor,
        role=actor.role,
        action=action,
        target=f"rights_request:{row.request_id}",
        reason=f"DPDP {row.kind} request",
    )


def open_request(
    session: Session,
    bus: EventBus,
    settings: Settings,
    sla: RightsSlaSettings,
    *,
    phone_e164: str,
    kind: RightsKind,
    at: datetime,
    actor: Actor,
) -> RightsRequestRow:
    row = RightsRequestRow(
        request_id=new_id("rr"),
        tenant_id=settings.tenant_id,
        kind=kind,
        phone_hash=phone_hash(phone_e164, settings.phone_pepper),
        received_at=at,
        ack_due_at=at + timedelta(hours=sla.ack_hours),
        due_at=at + timedelta(days=sla.resolve_days),
        status="open",
        acknowledged_at=None,
        completed_at=None,
        result={},
    )
    session.add(row)
    session.flush()
    _audit(session, bus, settings, row, actor, "rights.open", at)
    return row


def get_request(session: Session, request_id: str) -> RightsRequestRow:
    row = session.get(RightsRequestRow, request_id)
    if row is None:
        raise NotFoundError(f"no rights request {request_id}")
    return row


def acknowledge(
    session: Session,
    bus: EventBus,
    settings: Settings,
    *,
    request_id: str,
    at: datetime,
    actor: Actor,
) -> RightsRequestRow:
    row = get_request(session, request_id)
    if row.status != "open":
        raise StateConflictError(f"request {request_id} is {row.status}")
    row.status = "acknowledged"
    row.acknowledged_at = at
    session.flush()
    _audit(session, bus, settings, row, actor, "rights.acknowledge", at)
    return row


def _complete(row: RightsRequestRow, at: datetime, result: dict[str, Any]) -> None:
    if row.status == "completed":
        raise StateConflictError(f"request {row.request_id} already completed")
    row.status = "completed"
    row.completed_at = at
    row.acknowledged_at = row.acknowledged_at or at
    row.result = result


def fulfil_access(
    session: Session,
    bus: EventBus,
    settings: Settings,
    cipher: DataCipher,
    *,
    request_id: str,
    phone_e164: str,
    at: datetime,
    actor: Actor,
) -> dict[str, Any]:
    row = _matching(session, settings, request_id, phone_e164, "access")
    outcomes = session.scalars(
        select(CallOutcomeRow).where(CallOutcomeRow.phone_hash == row.phone_hash)
    )
    transcripts = session.scalars(
        select(TranscriptRow).where(TranscriptRow.phone_hash == row.phone_hash)
    )
    export: dict[str, Any] = {
        "consents": [c.model_dump(mode="json") for c in consents_for(session, phone_e164)],
        "calls": [o.payload for o in outcomes],
        "transcripts": {t.call_id: cipher.decrypt_json(t.ciphertext) for t in transcripts},
    }
    _complete(row, at, {"exported_calls": len(export["calls"])})
    session.flush()
    _audit(session, bus, settings, row, actor, "rights.access", at)
    return export


def fulfil_correction(
    session: Session,
    bus: EventBus,
    settings: Settings,
    *,
    request_id: str,
    phone_e164: str,
    at: datetime,
    actor: Actor,
    note: str,
) -> RightsRequestRow:
    """Booking data is Agoda's record; we route the correction to Agoda and keep the trail."""
    row = _matching(session, settings, request_id, phone_e164, "correction")
    _complete(row, at, {"routed_to": "agoda_booking_record_owner", "note": note})
    session.flush()
    _audit(session, bus, settings, row, actor, "rights.correction", at)
    return row


@dataclass(frozen=True)
class ErasureCounts:
    transcripts: int
    audio: int
    outcomes_pseudonymised: int


def fulfil_erasure(
    session: Session,
    bus: EventBus,
    settings: Settings,
    *,
    request_id: str,
    phone_e164: str,
    at: datetime,
    actor: Actor,
) -> ErasureCounts:
    row = _matching(session, settings, request_id, phone_e164, "erasure")
    ph = row.phone_hash
    transcripts = session.execute(
        delete(TranscriptRow).where(TranscriptRow.phone_hash == ph)
    ).rowcount
    audio = session.execute(delete(AudioRefRow).where(AudioRefRow.phone_hash == ph)).rowcount
    outcomes = list(session.scalars(select(CallOutcomeRow).where(CallOutcomeRow.phone_hash == ph)))
    for outcome in outcomes:
        # Keeps the row for lift analytics; drops the link back to the person.
        outcome.phone_hash = ERASED
        outcome.booking_id = f"{ERASED}-{sha256_hex(outcome.booking_id)[:12]}"
        outcome.payload = {**outcome.payload, "booking_id": outcome.booking_id}
    counts = ErasureCounts(
        transcripts=transcripts, audio=audio, outcomes_pseudonymised=len(outcomes)
    )
    _complete(
        row,
        at,
        {
            "transcripts": transcripts,
            "audio": audio,
            "outcomes": len(outcomes),
            "retained": ["consent_records", "opt_outs"],
        },
    )
    session.flush()
    _audit(session, bus, settings, row, actor, "rights.erasure", at)
    return counts


def _matching(
    session: Session, settings: Settings, request_id: str, phone_e164: str, kind: RightsKind
) -> RightsRequestRow:
    row = get_request(session, request_id)
    if row.kind != kind:
        raise StateConflictError(f"request {request_id} is {row.kind}, not {kind}")
    if row.phone_hash != phone_hash(phone_e164, settings.phone_pepper):
        raise StateConflictError("phone number does not match the request")
    return row


@dataclass(frozen=True)
class OverdueRequests:
    unacknowledged: list[str]
    unresolved: list[str]


def overdue(session: Session, now: datetime) -> OverdueRequests:
    open_rows = list(
        session.scalars(select(RightsRequestRow).where(RightsRequestRow.status != "completed"))
    )
    return OverdueRequests(
        unacknowledged=[
            r.request_id for r in open_rows if r.status == "open" and now >= r.ack_due_at
        ],
        unresolved=[r.request_id for r in open_rows if now >= r.due_at],
    )


def list_requests(session: Session, limit: int) -> list[RightsRequestRow]:
    stmt = select(RightsRequestRow).order_by(RightsRequestRow.received_at.desc()).limit(limit)
    return list(session.scalars(stmt))
