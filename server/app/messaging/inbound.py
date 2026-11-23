"""Inbound WhatsApp handling. A one-word reply withdraws consent (REQ-DPDP-03)."""

from __future__ import annotations

import re
from typing import Literal

from sqlalchemy.orm import Session

from app.compliance.consent import mark_dnc
from app.core.clock import Clock
from app.core.config import Settings
from app.messaging.whatsapp import record_inbound

_WITHDRAW = re.compile(
    r"^\s*(stop|unsubscribe|band karo|call mat karo|mat karo|नहीं चाहिए|बंद करो|रोकें)\s*[.!]*\s*$",
    re.IGNORECASE,
)

InboundAction = Literal["withdrawn", "recorded"]


def handle_inbound(
    session: Session, settings: Settings, clock: Clock, *, phone_e164: str, text: str
) -> InboundAction:
    record_inbound(session, settings, phone_e164, clock)
    if _WITHDRAW.match(text):
        mark_dnc(
            session,
            settings,
            phone_e164=phone_e164,
            at=clock.now(),
            channel="whatsapp",
            call_id=None,
        )
        return "withdrawn"
    return "recorded"
