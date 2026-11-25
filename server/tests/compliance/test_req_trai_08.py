"""REQ-TRAI-08: <= 2 attempts per booking_event, >= 24 h per number across campaigns, <= 1 WA fallback."""

from datetime import timedelta

import pytest
from hypothesis import settings as hsettings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from app.compliance.evaluate import evaluate
from app.core.bus import MemoryBus
from app.core.clock import FrozenClock
from app.core.db import create_all, make_engine, make_session_factory
from app.core.errors import AttemptCapError, CooldownError, FallbackCapError, GateError
from app.messaging.whatsapp import send_no_answer_fallback
from app.providers.telephony.mock import MockTelephony
from app.providers.whatsapp.mock import MockWhatsApp
from app.telephony.dial import dial
from tests.compliance.helpers import NOON_IST
from tests.factories import SERVICE_CLI, make_event, make_settings, seed_cli, seed_consent


def _dial(session, settings, clock, bus, tel, event):
    clearance = evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)
    return dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)


def test_second_attempt_needs_cooldown_third_is_capped(session, settings, clock, bus):
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    tel = MockTelephony()
    _dial(session, settings, clock, bus, tel, event)
    clock.advance(timedelta(hours=23, minutes=59, seconds=59))
    with pytest.raises(CooldownError):
        _dial(session, settings, clock, bus, tel, event)
    clock.advance(timedelta(seconds=1))
    _dial(session, settings, clock, bus, tel, event)
    clock.advance(timedelta(days=2))
    with pytest.raises(AttemptCapError):
        _dial(session, settings, clock, bus, tel, event)
    assert len(tel.placed) == 2


def test_cooldown_spans_events_for_the_same_number(session, settings, clock, bus):
    first = make_event(settings)
    second = make_event(settings, booking_id=None)
    seed_cli(session, settings)
    seed_consent(session, settings, first)
    seed_consent(session, settings, second)
    tel = MockTelephony()
    _dial(session, settings, clock, bus, tel, first)
    with pytest.raises(CooldownError):
        _dial(session, settings, clock, bus, tel, second)


def test_one_whatsapp_fallback_per_event(session, settings, clock):
    event = make_event(settings)
    wa = MockWhatsApp()
    send_no_answer_fallback(session, settings, clock, wa, event)
    with pytest.raises(FallbackCapError):
        send_no_answer_fallback(session, settings, clock, wa, event)
    assert len(wa.sent) == 1


class AttemptMachine(RuleBasedStateMachine):
    """Random sequences of time passing and dial attempts never break the caps."""

    @initialize()
    def setup(self) -> None:
        self.settings = make_settings()
        engine = make_engine("sqlite://")
        create_all(engine)
        self.session = make_session_factory(engine)()
        self.clock = FrozenClock(NOON_IST)
        self.bus = MemoryBus()
        self.tel = MockTelephony()
        self.event = make_event(self.settings)
        seed_cli(self.session, self.settings)
        seed_consent(self.session, self.settings, self.event)
        self.dial_times: list = []

    @rule(hours=st.integers(min_value=1, max_value=30))
    def wait(self, hours: int) -> None:
        self.clock.advance(timedelta(hours=hours))

    @rule()
    def attempt(self) -> None:
        try:
            _dial(self.session, self.settings, self.clock, self.bus, self.tel, self.event)
        except GateError:
            return
        self.dial_times.append(self.clock.now())

    @invariant()
    def caps_hold(self) -> None:
        if not hasattr(self, "dial_times"):
            return
        assert len(self.dial_times) <= 2
        for a, b in zip(self.dial_times, self.dial_times[1:], strict=False):
            assert b - a >= timedelta(hours=24)


AttemptMachine.TestCase.settings = hsettings(max_examples=60, stateful_step_count=15, deadline=None)
TestAttemptMachine = AttemptMachine.TestCase
