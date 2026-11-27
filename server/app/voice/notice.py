"""The itemised DPDP notice sent by WhatsApp/SMS link (REQ-DPDP-01).

The first utterance names the purpose and the recording; this notice carries
the full item list the DPDP Rules require.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.types import Purpose

_PURPOSE_TEXT: dict[Purpose, str] = {
    "J1": "Helping you complete the pending payment for your {client} booking by sending a payment link.",
    "J2": "Confirming your {client} booking details (dates, guests, arrival time, special requests) before arrival.",
}

_DATA_ITEMS: dict[Purpose, tuple[str, ...]] = {
    "J1": (
        "your first name",
        "your phone number",
        "the city of your booking",
        "the amount due and payment due date",
        "the call recording and a redacted transcript",
    ),
    "J2": (
        "your first name",
        "your phone number",
        "property name, city and check-in/check-out dates",
        "number of guests",
        "arrival time and special requests you give us",
        "the call recording and a redacted transcript",
    ),
}


@dataclass(frozen=True)
class Notice:
    purpose: str
    data_items: tuple[str, ...]
    recording: str
    ai_disclosure: str
    rights: tuple[str, ...]
    how_to_withdraw: str
    grievance_contact: str
    board_complaint: str
    retention: str
    url: str


def build_notice(settings: Settings, purpose: Purpose) -> Notice:
    return Notice(
        purpose=_PURPOSE_TEXT[purpose].format(client=settings.client.name),
        data_items=_DATA_ITEMS[purpose],
        recording="This call is recorded.",
        ai_disclosure=f"The caller is an AI assistant acting on behalf of {settings.client.name}.",
        rights=(
            "access a summary of your personal data we process",
            "correct or complete your data",
            "erase your data",
            "nominate another person to exercise your rights",
            "withdraw consent at any time",
        ),
        how_to_withdraw='Say "call mat karo" or "don\'t call" on any call, or reply STOP to this WhatsApp message.',
        grievance_contact=settings.grievance.channel,
        board_complaint="You may complain to the Data Protection Board of India if your grievance is not resolved.",
        retention=(
            f"Audio is kept {settings.retention.audio_days} days and redacted transcripts "
            f"{settings.retention.transcript_days} days, then deleted."
        ),
        url=settings.grievance.notice_url,
    )
