from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.campaigns import phase2
from app.campaigns.journeys import JourneyRules, plan_journey
from app.core.errors import NotBuiltYetError
from tests.factories import make_event

NOW = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)
RULES = JourneyRules()


def test_failed_payment_is_due_now(settings):
    plan = plan_journey(make_event(settings, status="payment_failed"), NOW, RULES)
    assert plan is not None and plan.purpose == "J1" and plan.due_at == NOW


def test_pending_payment_waits_for_threshold(settings):
    event = make_event(settings, status="payment_pending", occurred_at=NOW.isoformat())
    plan = plan_journey(event, NOW, RULES)
    assert plan is not None and plan.due_at == NOW + timedelta(hours=2)


def test_no_call_after_payment_date(settings):
    event = make_event(
        settings, status="payment_pending", payment_due_at=(NOW - timedelta(seconds=1)).isoformat()
    )
    assert plan_journey(event, NOW, RULES) is None


def test_cancelled_starts_nothing(settings):
    assert plan_journey(make_event(settings, status="cancelled"), NOW, RULES) is None


def test_confirmed_is_called_two_days_before_check_in(settings):
    event = make_event(settings, status="confirmed")  # check-in 12 Dec 2026
    plan = plan_journey(event, NOW, RULES)
    assert plan is not None and plan.purpose == "J2"
    assert plan.due_at == datetime(2026, 12, 10, 5, 30, tzinfo=UTC)  # 11:00 IST


def test_purpose_not_allowed_starts_nothing(settings):
    event = make_event(settings, status="confirmed", purposes_allowed=["J1"])
    assert plan_journey(event, NOW, RULES) is None


def test_phase2_stubs_raise_with_ticket(settings):
    calls = [
        (lambda: phase2.start_inbound_support("+919812345678"), "AV-J4"),
        (lambda: phase2.import_supply_leads(Path("leads.csv")), "AV-J5"),
        (phase2.contact_drivers, "AV-J6"),
        (lambda: phase2.offer_connected_trip(make_event(settings)), "AV-J7"),
    ]
    for call, ticket in calls:
        with pytest.raises(NotBuiltYetError) as info:
            call()
        assert info.value.ticket == ticket
