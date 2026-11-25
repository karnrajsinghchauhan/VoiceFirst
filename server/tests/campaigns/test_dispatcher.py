from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.campaigns.dispatcher import Dispatcher
from app.campaigns.journeys import JourneyRules
from app.campaigns.models import HoldoutMemberRow, QueueItemRow
from app.compliance.killswitch import engage
from app.compliance.models import ClearanceRow, DialAttemptRow, GateDecisionRow
from app.core.db import transaction
from app.core.errors import ProviderError
from app.providers.telephony.mock import MockTelephony
from tests.campaigns.stubs import FixedRunner, RecordingFallback
from tests.factories import SERVICE_CLI, booking_id_with_holdout, make_event, seed_cli, seed_consent


@pytest.fixture
def tel() -> MockTelephony:
    return MockTelephony()


@pytest.fixture
def fallback() -> RecordingFallback:
    return RecordingFallback()


def _dispatcher(session_factory, bus, settings, clock, tel, runner, fallback) -> Dispatcher:
    return Dispatcher(
        session_factory=session_factory,
        bus=bus,
        settings=settings,
        clock=clock,
        telephony=tel,
        runner=runner,
        fallback=fallback,
        cli_by_purpose={"J1": SERVICE_CLI, "J2": SERVICE_CLI},
        rules=JourneyRules(),
    )


def _ready(session_factory, settings, event, **consent):
    with transaction(session_factory) as s:
        seed_cli(s, settings)
        seed_consent(s, settings, event, **consent)


def _payload(event):
    return event.model_dump(mode="json")


def _failed_event(settings, **kw):
    return make_event(settings, status="payment_failed", **kw)


def test_payment_failed_is_dialled_and_finished(
    session_factory, bus, settings, clock, tel, fallback
):
    event = _failed_event(settings)
    _ready(session_factory, settings, event)
    runner = FixedRunner(clock, "link_sent")
    d = _dispatcher(session_factory, bus, settings, clock, tel, runner, fallback)
    d.ingest(_payload(event))
    results = d.run_due()
    assert [r.state for r in results] == ["done"]
    assert len(tel.placed) == 1 and len(runner.calls) == 1
    assert len(bus.messages["av.booking-events.v1"]) == 1
    assert fallback.sent == []


def test_redelivered_event_is_a_noop(session_factory, bus, settings, clock, tel, fallback):
    event = _failed_event(settings)
    _ready(session_factory, settings, event)
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(event))
    d.ingest(_payload(event))
    with transaction(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(QueueItemRow)) == 1


def test_held_out_booking_is_recorded_and_never_dialled(
    session_factory, bus, settings, clock, tel, fallback
):
    event = _failed_event(settings, booking_id=booking_id_with_holdout(settings, True))
    _ready(session_factory, settings, event)
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(event))
    assert [r.state for r in d.run_due()] == ["held_out"]
    assert tel.placed == []
    with transaction(session_factory) as s:
        assert s.get(HoldoutMemberRow, event.booking_id) is not None
        assert s.scalar(select(func.count()).select_from(GateDecisionRow)) == 1


def test_no_answer_sends_one_fallback_then_retries_after_cooldown(
    session_factory, bus, settings, clock, tel, fallback
):
    event = _failed_event(settings)
    _ready(session_factory, settings, event)
    runner = FixedRunner(clock, "no_answer")
    d = _dispatcher(session_factory, bus, settings, clock, tel, runner, fallback)
    d.ingest(_payload(event))
    assert [r.state for r in d.run_due()] == ["queued"]
    assert fallback.sent == [event.event_id]
    clock.advance(timedelta(hours=23, minutes=59))
    assert d.run_due() == []
    clock.advance(timedelta(minutes=1))
    assert [r.state for r in d.run_due()] == ["done"]
    assert len(tel.placed) == 2
    assert fallback.sent == [event.event_id]
    clock.advance(timedelta(days=3))
    assert d.run_due() == []


def test_missing_consent_blocks_without_dialling(
    session_factory, bus, settings, clock, tel, fallback
):
    event = _failed_event(settings)
    with transaction(session_factory) as s:
        seed_cli(s, settings)
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(event))
    results = d.run_due()
    assert [(r.state, r.reason) for r in results] == [("blocked", "consent_missing")]
    assert tel.placed == []


def test_outside_window_is_requeued_not_blocked(
    session_factory, bus, settings, clock, tel, fallback
):
    clock.advance(timedelta(hours=9))  # 21:00 IST
    event = _failed_event(settings)
    _ready(session_factory, settings, event)
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(event))
    assert [(r.state, r.reason) for r in d.run_due()] == [("queued", "outside_call_window")]
    assert tel.placed == []


def test_kill_switch_drops_queued_dials(session_factory, bus, settings, clock, tel, fallback):
    event = _failed_event(settings)
    _ready(session_factory, settings, event)
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(event))
    with transaction(session_factory) as s:
        engage(
            s,
            bus,
            clock,
            tenant_id=settings.tenant_id,
            actor="ops@prosperops",
            role="ops",
            reason="test",
        )
    assert d.run_due() == []
    assert tel.placed == []
    with transaction(session_factory) as s:
        assert s.scalar(select(QueueItemRow.state)) == "dropped"


def test_newer_event_supersedes_queued_call(session_factory, bus, settings, clock, tel, fallback):
    pending = make_event(settings, status="payment_pending")
    _ready(session_factory, settings, pending)
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(pending))
    paid = make_event(settings, booking_id=pending.booking_id, status="cancelled")
    d.ingest(_payload(paid))
    clock.advance(timedelta(hours=3))
    assert d.run_due() == []
    assert tel.placed == []


def test_provider_failure_keeps_gate_decision_and_raises(
    session_factory, bus, settings, clock, tel, fallback
):
    event = _failed_event(settings)
    _ready(session_factory, settings, event)
    tel.fail_next = True
    d = _dispatcher(
        session_factory, bus, settings, clock, tel, FixedRunner(clock, "link_sent"), fallback
    )
    d.ingest(_payload(event))
    with pytest.raises(ProviderError):
        d.run_due()
    with transaction(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(GateDecisionRow)) == 1
        assert s.scalar(select(func.count()).select_from(DialAttemptRow)) == 0
        assert s.scalar(select(ClearanceRow.consumed_at)) is None
        assert s.scalar(select(QueueItemRow.state)) == "error"
