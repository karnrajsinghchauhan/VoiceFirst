"""D-036: a booking carries a stay or an appointment; appointments plan J2 before the slot."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.campaigns.journeys import JourneyRules, booking_shape, plan_journey
from app.contracts.generated.booking_event import BookingEvent
from app.core.errors import EventShapeError
from app.voice.context import PurposeContext
from tests.factories import make_event

NOW = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)


def _appointment(settings, slot: datetime) -> BookingEvent:
    base = make_event(settings).model_dump(mode="json")
    base.pop("property")
    base.pop("stay")
    base.update(
        status="confirmed",
        purposes_allowed=["J2"],
        appointment={
            "kind": "home_inspection",
            "slot_start": slot.isoformat(),
            "area": "Andheri West",
        },
    )
    return BookingEvent.model_validate(base)


def test_appointment_is_planned_ahead_of_the_slot(settings):
    event = _appointment(settings, NOW + timedelta(days=1))
    plan = plan_journey(event, NOW, JourneyRules())
    assert plan is not None and plan.purpose == "J2"
    assert plan.due_at == NOW + timedelta(days=1) - JourneyRules().appointment_lead


def test_a_past_slot_starts_no_journey(settings):
    assert (
        plan_journey(_appointment(settings, NOW - timedelta(hours=1)), NOW, JourneyRules()) is None
    )


def test_an_event_with_both_shapes_is_refused(settings):
    both = _appointment(settings, NOW + timedelta(days=1)).model_copy(
        update={"stay": make_event(settings).stay, "property": make_event(settings).property}
    )
    with pytest.raises(EventShapeError):
        booking_shape(both)


def test_an_event_with_neither_shape_is_refused(settings):
    neither = make_event(settings).model_copy(update={"stay": None})
    with pytest.raises(EventShapeError):
        booking_shape(neither)


def test_j2_reads_the_appointment_and_j1_cannot(settings):
    event = _appointment(settings, NOW + timedelta(days=1))
    ctx = PurposeContext(event, "J2")
    assert ctx.get("appointment.area") == "Andheri West"
    assert ctx.get("stay.check_in") is None
