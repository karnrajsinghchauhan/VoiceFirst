from app.compliance.evaluate import evaluate
from app.providers.telephony.mock import MockTelephony
from app.telephony.dial import dial
from tests.factories import make_event, seed_cli, seed_consent


def test_happy_path_dials_once(session, settings, clock, bus):
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    clearance = evaluate(session, bus, settings, clock, event, "J1", "+911600123456")
    tel = MockTelephony()
    handle = dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert tel.placed == [(event.customer.phone_e164, "+911600123456", handle.call_id)]
    assert len(bus.messages["av.gate-decisions.v1"]) == 1
