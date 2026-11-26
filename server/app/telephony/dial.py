"""telephony.dial: the only function that places a call (9.1). Only campaigns.dispatcher may import it."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.compliance.clearance import GateClearance
from app.compliance.models import ClearanceRow, DialAttemptRow
from app.compliance.repository import kill_switch_engaged
from app.core.clock import Clock
from app.core.errors import ClearanceInvalidError, KillSwitchEngagedError
from app.core.ids import new_id, phone_hash
from app.providers.base import TelephonyProvider


@dataclass(frozen=True)
class CallHandle:
    call_id: str
    provider_call_id: str
    clearance: GateClearance


def dial(
    session: Session,
    clearance: GateClearance,
    provider: TelephonyProvider,
    clock: Clock,
    tenant_id: str,
    pepper: str,
) -> CallHandle:
    """Consumes the clearance and places the call in one transaction (owned by the caller).

    The CLI shown is the clearance's declared CLI; no parameter can change it (REQ-CLI-01).
    """
    now = clock.now()
    consumed = session.execute(
        update(ClearanceRow)
        .where(
            ClearanceRow.clearance_id == clearance.clearance_id,
            ClearanceRow.consumed_at.is_(None),
            ClearanceRow.expires_at > now,
            ClearanceRow.phone_e164 == clearance.phone_e164,
            ClearanceRow.cli_e164 == clearance.cli_e164,
            ClearanceRow.booking_event_id == clearance.booking_event_id,
            ClearanceRow.purpose == clearance.purpose,
        )
        .values(consumed_at=now)
    )
    if consumed.rowcount != 1:
        raise ClearanceInvalidError("clearance unknown, expired, consumed or altered")
    # A clearance minted just before the kill switch must not dial (P5).
    if kill_switch_engaged(session, tenant_id):
        raise KillSwitchEngagedError("kill switch engaged after clearance was minted")
    call_id = new_id("call")
    placed = provider.place_call(clearance.phone_e164, clearance.cli_e164, call_id)
    session.add(
        DialAttemptRow(
            attempt_id=new_id("att"),
            clearance_id=clearance.clearance_id,
            booking_event_id=clearance.booking_event_id,
            booking_id=clearance.booking_id,
            phone_hash=phone_hash(clearance.phone_e164, pepper),
            cli_e164=clearance.cli_e164,
            dialled_at=now,
            provider_call_id=placed.provider_call_id,
            call_id=call_id,
        )
    )
    session.flush()
    return CallHandle(
        call_id=call_id, provider_call_id=placed.provider_call_id, clearance=clearance
    )
