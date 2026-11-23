"""REQ-DPDP-03: withdrawal is as easy as giving consent: one WhatsApp reply (voice path: tests/voice)."""

import pytest

from app.compliance.consent import record_consent
from app.compliance.evaluate import evaluate
from app.core.errors import ConsentExpiredError, OptOutLockoutError
from app.messaging.inbound import handle_inbound
from tests.factories import SERVICE_CLI, make_event, seed_cli


@pytest.mark.parametrize("reply", ["STOP", "stop", " Stop. ", "band karo", "बंद करो"])
def test_one_reply_withdraws_and_blocks_the_next_dial(session, settings, clock, bus, reply):
    event = make_event(settings)
    seed_cli(session, settings)
    record_consent(
        session,
        settings,
        phone_e164=event.customer.phone_e164,
        basis="explicit",
        purpose="J1",
        channel="whatsapp",
        obtained_at=clock.now(),
        booking_id=None,
        source_ref="customer_reply",
        trace_id=event.trace_id,
    )
    evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)  # consent works first
    assert (
        handle_inbound(session, settings, clock, phone_e164=event.customer.phone_e164, text=reply)
        == "withdrawn"
    )
    with pytest.raises((ConsentExpiredError, OptOutLockoutError)):
        evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)


@pytest.mark.parametrize("reply", ["ok thanks", "stop calling me at night please call at 6"])
def test_other_replies_do_not_withdraw(session, settings, clock, reply):
    assert (
        handle_inbound(session, settings, clock, phone_e164="+919812345678", text=reply)
        == "recorded"
    )
