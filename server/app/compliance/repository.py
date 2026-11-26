"""Loads a GateContext from the database. The only reader of compliance tables for gating."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.compliance.context import (
    CallPurpose,
    CliView,
    ConsentView,
    GateContext,
)
from app.compliance.models import (
    CampaignPauseRow,
    CliRow,
    ConsentRow,
    DialAttemptRow,
    KillSwitchRow,
    OptOutRow,
    PreferenceRow,
)
from app.contracts.generated.booking_event import BookingEvent
from app.core.config import Settings
from app.core.ids import phone_hash


def kill_switch_engaged(session: Session, tenant_id: str) -> bool:
    row = session.get(KillSwitchRow, tenant_id)
    return row is not None and row.engaged


def campaigns_paused(session: Session, tenant_id: str) -> bool:
    stmt = (
        select(func.count())
        .select_from(CampaignPauseRow)
        .where(CampaignPauseRow.tenant_id == tenant_id, CampaignPauseRow.lifted_at.is_(None))
    )
    return session.scalar(stmt) != 0


def _consents(session: Session, phone_e164: str) -> tuple[ConsentView, ...]:
    rows = session.scalars(select(ConsentRow).where(ConsentRow.phone_e164 == phone_e164))
    return tuple(
        ConsentView(
            basis=r.basis,
            purpose=r.purpose,
            booking_id=r.booking_id,
            obtained_at=r.obtained_at,
            expires_at=r.expires_at,
            revoked_at=r.revoked_at,
        )
        for r in rows
    )


def _cli(session: Session, cli_e164: str) -> CliView | None:
    row = session.get(CliRow, cli_e164)
    if row is None:
        return None
    return CliView(
        cli_e164=row.cli_e164,
        series=row.series,
        purpose=row.purpose,
        oap=row.oap,
        a2p_declared=row.a2p_declared,
        declaration_ref=row.declaration_ref,
        dlt_recorded_at=row.dlt_recorded_at,
        status=row.status,
    )


def load_context(
    session: Session,
    settings: Settings,
    event: BookingEvent,
    purpose: CallPurpose,
    cli_e164: str,
    now: datetime,
) -> GateContext:
    phone = event.customer.phone_e164
    ph = phone_hash(phone, settings.phone_pepper)
    pref = session.get(PreferenceRow, ph)
    opt_out = session.get(OptOutRow, ph)
    attempts = session.scalar(
        select(func.count())
        .select_from(DialAttemptRow)
        .where(DialAttemptRow.booking_event_id == event.event_id)
    )
    last_dial = session.scalar(
        select(func.max(DialAttemptRow.dialled_at)).where(DialAttemptRow.phone_hash == ph)
    )
    return GateContext(
        event=event,
        purpose=purpose,
        now=now,
        kill_switch_engaged=kill_switch_engaged(session, event.tenant_id),
        campaigns_paused=campaigns_paused(session, event.tenant_id),
        consents=_consents(session, phone),
        preference=pref.state if pref else "none",
        opted_out_at=opt_out.opted_out_at if opt_out else None,
        cli=_cli(session, cli_e164),
        attempts_for_event=attempts or 0,
        last_dial_at_for_number=last_dial,
        compliance=settings.compliance,
        holdout=settings.holdout,
    )
