"""REQ-TRAI-05: opt-out -> no dial and no consent request for 90 days."""

from datetime import timedelta

import pytest

from app.compliance.consent import assert_may_request_consent, mark_dnc, record_consent
from app.compliance.evaluate import evaluate
from app.core.errors import OptOutLockoutError
from tests.factories import SERVICE_CLI, make_event, seed_cli, seed_consent


def test_opt_out_blocks_dial_and_consent_requests_for_90_days(session, settings, clock, bus):
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    phone = event.customer.phone_e164
    mark_dnc(session, settings, phone_e164=phone, at=clock.now(), channel="voice", call_id="c1")
    start = clock.now()
    for day in (0, 1, 30, 89):
        probe = start + timedelta(days=day)
        clock.set(probe)
        with pytest.raises(OptOutLockoutError):
            assert_may_request_consent(session, settings, phone_e164=phone, now=probe)
        with pytest.raises(Exception) as exc:
            evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)
        # Consent was revoked by the opt-out, so the consent gate fails first; the lock is the backstop.
        assert exc.value.__class__.__name__ in {"ConsentExpiredError", "OptOutLockoutError"}


def test_lock_is_backstop_even_with_new_transaction_basis(session, settings, clock, bus):
    event = make_event(settings)
    seed_cli(session, settings)
    phone = event.customer.phone_e164
    mark_dnc(session, settings, phone_e164=phone, at=clock.now(), channel="voice", call_id="c1")
    # A later booking creates a fresh transaction relationship; the opt-out still holds.
    clock.advance(timedelta(days=5))
    seed_consent(session, settings, event, obtained_at=clock.now())
    with pytest.raises(OptOutLockoutError):
        evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)


def test_consent_request_allowed_after_90_days(session, settings, clock):
    phone = "+919812345678"
    mark_dnc(session, settings, phone_e164=phone, at=clock.now(), channel="voice", call_id=None)
    assert_may_request_consent(
        session, settings, phone_e164=phone, now=clock.now() + timedelta(days=90)
    )


def test_customer_explicit_reconsent_reopens(session, settings, clock, bus):
    event = make_event(settings)
    seed_cli(session, settings)
    phone = event.customer.phone_e164
    mark_dnc(session, settings, phone_e164=phone, at=clock.now(), channel="voice", call_id=None)
    clock.advance(timedelta(days=2))
    record_consent(
        session,
        settings,
        phone_e164=phone,
        basis="explicit",
        purpose="J1",
        channel="whatsapp",
        obtained_at=clock.now(),
        booking_id=None,
        source_ref="customer_initiated",
        trace_id=event.trace_id,
    )
    evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)
