"""CSAT survey over a WhatsApp utility template. Whether this is allowed, and its text, are [CD]."""

from __future__ import annotations

from typing import Protocol

from app.contracts.generated.booking_event import BookingEvent

# [CD] template name and text; discovery question 23.
CSAT_TEMPLATE = "av_csat_survey_v1"


class CsatSurveySender(Protocol):
    """Implemented by messaging/: sends CSAT_TEMPLATE only to opted-in numbers, once per call."""

    def send_csat_survey(self, event: BookingEvent, call_id: str) -> None: ...
