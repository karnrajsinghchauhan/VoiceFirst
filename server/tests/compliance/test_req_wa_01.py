"""REQ-WA-01: templates only to numbers with a recorded opt-in (source and timestamp)."""

import json
from pathlib import Path

import pytest

from app.core.errors import WhatsAppOptInMissingError
from app.messaging.whatsapp import send_no_answer_fallback, send_payment_link
from app.providers.whatsapp.mock import MockWhatsApp
from tests.factories import make_event

SCHEMA = json.loads(
    (Path(__file__).parents[3] / "contracts/schemas/booking_event.json").read_text()
)


@pytest.mark.parametrize("send", [send_payment_link, send_no_answer_fallback])
def test_no_opt_in_no_send(session, settings, clock, send) -> None:
    event = make_event(settings, customer={"whatsapp_opt_in": None})
    wa = MockWhatsApp()
    with pytest.raises(WhatsAppOptInMissingError):
        send(session, settings, clock, wa, event)
    assert wa.sent == []


def test_opt_in_requires_source_and_timestamp() -> None:
    opt_in = SCHEMA["properties"]["customer"]["properties"]["whatsapp_opt_in"]["oneOf"][1]
    assert set(opt_in["required"]) == {"at", "source"}


def test_opted_in_send_is_recorded(session, settings, clock) -> None:
    from app.compliance.models import WhatsAppSendRow

    wa = MockWhatsApp()
    send_payment_link(session, settings, clock, wa, make_event(settings))
    row = session.query(WhatsAppSendRow).one()
    assert row.kind == "in_call" and row.template == "av_payment_link_v1"
