"""Consent records, opt-out (mark_dnc) and the 90-day no-re-request lock (REQ-TRAI-03, -05, DPDP-03)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.compliance.models import ConsentRow, OptOutRow
from app.contracts.generated.consent_record import ConsentRecord
from app.core.config import Settings
from app.core.errors import OptOutLockoutError
from app.core.ids import new_id, phone_hash

Basis = Literal["transaction", "explicit", "inquiry"]
Channel = Literal["voice", "whatsapp", "sms", "web", "dca"]


def expiry_for(settings: Settings, basis: Basis, obtained_at: datetime) -> datetime | None:
    """Explicit and inquiry consent last 7 days; a transaction basis lasts while the booking is live."""
    if basis == "explicit":
        return obtained_at + timedelta(days=settings.compliance.explicit_consent_days)
    if basis == "inquiry":
        return obtained_at + timedelta(days=settings.compliance.inquiry_days)
    return None


def record_consent(
    session: Session, settings: Settings, *, phone_e164: str, basis: Basis, purpose: str,
    channel: Channel, obtained_at: datetime, booking_id: str | None, source_ref: str,
    trace_id: str, evidence_uri: str | None = None,
) -> ConsentRecord:
    row = ConsentRow(
        consent_id=new_id("cns"), tenant_id=settings.tenant_id, phone_e164=phone_e164,
        basis=basis, purpose=purpose, channel=channel, booking_id=booking_id,
        obtained_at=obtained_at, expires_at=expiry_for(settings, basis, obtained_at),
        revoked_at=None, source_ref=source_ref, consent_manager_id=None, artefact_ref=None,
        evidence_uri=evidence_uri, trace_id=trace_id,
    )
    session.add(row)
    session.flush()
    return to_record(row)


def to_record(row: ConsentRow) -> ConsentRecord:
    return ConsentRecord(
        schema_version="1.0.0", tenant_id=row.tenant_id, trace_id=row.trace_id,
        consent_id=row.consent_id, phone_e164=row.phone_e164, basis=row.basis,
        purpose=row.purpose,  # type: ignore[arg-type]
        channel=row.channel,  # type: ignore[arg-type]
        obtained_at=row.obtained_at, expires_at=row.expires_at, revoked_at=row.revoked_at,
        source_ref=row.source_ref, consent_manager_id=row.consent_manager_id,
        artefact_ref=row.artefact_ref, evidence_uri=row.evidence_uri,
    )


def mark_dnc(
    session: Session, settings: Settings, *, phone_e164: str, at: datetime, channel: Channel,
    call_id: str | None,
) -> None:
    """Opt-out: revokes every live consent for the number and starts the 90-day lock."""
    session.execute(
        update(ConsentRow)
        .where(ConsentRow.phone_e164 == phone_e164, ConsentRow.revoked_at.is_(None))
        .values(revoked_at=at)
    )
    session.merge(OptOutRow(phone_hash=phone_hash(phone_e164, settings.phone_pepper),
                            opted_out_at=at, channel=channel, call_id=call_id))
    session.flush()


def assert_may_request_consent(
    session: Session, settings: Settings, *, phone_e164: str, now: datetime
) -> None:
    """Raises OptOutLockoutError within 90 days of an opt-out (Second Amendment)."""
    row = session.get(OptOutRow, phone_hash(phone_e164, settings.phone_pepper))
    if row is None:
        return
    if now < row.opted_out_at + timedelta(days=settings.compliance.opt_out_lock_days):
        raise OptOutLockoutError("consent may not be re-requested within 90 days of opt-out")


def consents_for(session: Session, phone_e164: str) -> list[ConsentRecord]:
    rows = session.scalars(select(ConsentRow).where(ConsentRow.phone_e164 == phone_e164))
    return [to_record(r) for r in rows]
