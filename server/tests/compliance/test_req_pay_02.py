"""REQ-PAY-02: payment only through an Agoda-hosted link sent over WhatsApp; no UPI collect."""

import inspect

from app.messaging import whatsapp
from app.providers import base
from app.providers.whatsapp.mock import MockWhatsApp
from tests.factories import make_event


def test_link_is_on_the_configured_agoda_host(session, settings, clock) -> None:
    wa = MockWhatsApp()
    whatsapp.send_payment_link(session, settings, clock, wa, make_event(settings))
    link = wa.sent[0]["params"]["link"]  # type: ignore[index]
    assert link.startswith(settings.payment_link.base_url + "/")


def test_link_does_not_embed_the_booking_id_or_phone(session, settings, clock) -> None:
    event = make_event(settings)
    link = whatsapp.payment_link(settings, event)
    assert event.booking_id not in link and event.customer.phone_e164 not in link


def test_no_collect_or_charge_capability_exists() -> None:
    surface = inspect.getsource(base) + inspect.getsource(whatsapp)
    for forbidden in ("collect", "charge", "capture", "refund", "debit"):
        assert forbidden not in surface.lower()
