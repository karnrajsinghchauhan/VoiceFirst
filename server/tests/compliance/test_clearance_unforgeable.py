"""9.1 / 9.3: GateClearance cannot be built outside compliance, and a forged one cannot dial."""

from dataclasses import replace
from datetime import timedelta

import pytest

from app.compliance.clearance import GateClearance
from app.compliance.evaluate import evaluate
from app.compliance.killswitch import engage
from app.core.errors import ClearanceForgeryError, ClearanceInvalidError, KillSwitchEngagedError
from app.providers.telephony.mock import MockTelephony
from app.telephony.dial import dial
from tests.factories import SERVICE_CLI, make_event, seed_cli, seed_consent

FIELDS = {
    "clearance_id": "clr_x",
    "decision_id": "gd_x",
    "trace_id": "0" * 32,
    "booking_event_id": "evt_x",
    "booking_id": "BK00000000",
    "phone_e164": "+919812345678",
    "cli_e164": SERVICE_CLI,
    "purpose": "J1",
}


def _cleared(session, settings, clock, bus):
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    return evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)


def test_direct_construction_raises(clock) -> None:
    with pytest.raises(ClearanceForgeryError):
        GateClearance(**FIELDS, issued_at=clock.now(), expires_at=clock.now())  # type: ignore[arg-type]


def test_construction_with_a_fake_token_raises(clock) -> None:
    with pytest.raises(ClearanceForgeryError):
        GateClearance(
            **FIELDS,
            issued_at=clock.now(),
            expires_at=clock.now(),  # type: ignore[arg-type]
            _mint=object(),
        )


def test_dataclasses_replace_cannot_launder(session, settings, clock, bus) -> None:
    real = _cleared(session, settings, clock, bus)
    with pytest.raises(ClearanceForgeryError):
        replace(real, phone_e164="+917000000000")


def test_bypassing_init_is_refused_by_dial(session, settings, clock, bus) -> None:
    forged = object.__new__(GateClearance)
    for key, value in FIELDS.items():
        object.__setattr__(forged, key, value)
    object.__setattr__(forged, "issued_at", clock.now())
    object.__setattr__(forged, "expires_at", clock.now() + timedelta(seconds=60))
    tel = MockTelephony()
    with pytest.raises(ClearanceInvalidError):
        dial(session, forged, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert tel.placed == []


def test_tampered_real_clearance_is_refused(session, settings, clock, bus) -> None:
    real = _cleared(session, settings, clock, bus)
    object.__setattr__(real, "phone_e164", "+917000000000")
    tel = MockTelephony()
    with pytest.raises(ClearanceInvalidError):
        dial(session, real, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert tel.placed == []


def test_single_use(session, settings, clock, bus) -> None:
    clearance = _cleared(session, settings, clock, bus)
    tel = MockTelephony()
    dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
    with pytest.raises(ClearanceInvalidError):
        dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert len(tel.placed) == 1


def test_expires_after_60_seconds(session, settings, clock, bus) -> None:
    clearance = _cleared(session, settings, clock, bus)
    assert clearance.expires_at - clearance.issued_at == timedelta(seconds=60)
    clock.advance(timedelta(seconds=60))
    with pytest.raises(ClearanceInvalidError):
        dial(session, clearance, MockTelephony(), clock, settings.tenant_id, settings.phone_pepper)


def test_kill_switch_after_minting_blocks_dial(session, settings, clock, bus) -> None:
    clearance = _cleared(session, settings, clock, bus)
    engage(
        session, bus, clock, tenant_id=settings.tenant_id, actor="karn", role="admin", reason="test"
    )
    tel = MockTelephony()
    with pytest.raises(KillSwitchEngagedError):
        dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert tel.placed == []


def test_provider_failure_leaves_no_attempt_and_raises(session, settings, clock, bus) -> None:
    from app.compliance.models import DialAttemptRow
    from app.core.errors import ProviderError

    clearance = _cleared(session, settings, clock, bus)
    tel = MockTelephony(fail_next=True)
    with pytest.raises(ProviderError):
        dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert session.query(DialAttemptRow).count() == 0


def test_gate_decision_written_even_when_refused(session, settings, clock, bus) -> None:
    from app.compliance.models import GateDecisionRow
    from app.core.errors import ConsentMissingError

    event = make_event(settings)
    seed_cli(session, settings)
    with pytest.raises(ConsentMissingError):
        evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)
    rows = session.query(GateDecisionRow).all()
    assert len(rows) == 1 and rows[0].clearance_id is None
    gates = {g["name"]: g for g in rows[0].gates}
    assert gates["consent"]["reason_code"] == "consent_missing"
    assert gates["window"]["reason_code"] == "not_evaluated"
    assert len(bus.messages["av.gate-decisions.v1"]) == 1
