"""REQ-WA-03: free-form replies only inside the 24 h window; quality "low" pauses and pages."""

from datetime import timedelta

import pytest

from app.core.errors import WhatsAppPausedError, WhatsAppWindowClosedError
from app.incidents.service import list_open
from app.messaging.inbound import handle_inbound
from app.messaging.whatsapp import poll_quality, send_free_form, send_payment_link
from app.providers.whatsapp.mock import MockWhatsApp
from tests.factories import make_event

PHONE = "+919812345678"


def test_no_inbound_no_free_form(session, settings, clock) -> None:
    with pytest.raises(WhatsAppWindowClosedError):
        send_free_form(session, settings, clock, MockWhatsApp(), PHONE, "hi", settings.tenant_id)


def test_window_boundaries(session, settings, clock) -> None:
    handle_inbound(session, settings, clock, phone_e164=PHONE, text="link nahi mila")
    wa = MockWhatsApp()
    clock.advance(timedelta(hours=23, minutes=59, seconds=59))
    send_free_form(session, settings, clock, wa, PHONE, "Dobara bhej rahe hain", settings.tenant_id)
    clock.advance(timedelta(seconds=1))
    with pytest.raises(WhatsAppWindowClosedError):
        send_free_form(session, settings, clock, wa, PHONE, "x", settings.tenant_id)


def test_low_quality_pauses_and_pages(session, settings, clock) -> None:
    wa = MockWhatsApp(rating="low")
    assert poll_quality(session, settings, clock, wa) == "low"
    assert any("WhatsApp" in i.summary for i in list_open(session, settings.tenant_id))
    with pytest.raises(WhatsAppPausedError):
        send_payment_link(session, settings, clock, wa, make_event(settings))


@pytest.mark.parametrize("rating", ["high", "medium"])
def test_other_ratings_do_not_pause(session, settings, clock, rating) -> None:
    wa = MockWhatsApp(rating=rating)
    poll_quality(session, settings, clock, wa)
    send_payment_link(session, settings, clock, wa, make_event(settings))
