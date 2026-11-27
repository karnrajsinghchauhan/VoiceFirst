"""Which journey, if any, a booking event starts, and when. Pure functions of the event and the clock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from app.contracts.generated.booking_event import Appointment, BookingEvent, Property, Stay
from app.core.errors import EventShapeError

_IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class JourneyRules:
    """Timing rules. Every default is a [CD] item to confirm with Agoda."""

    # A pending payment is chased only after it has been pending this long.
    payment_pending_threshold: timedelta = timedelta(hours=2)
    # J2 calls go out this long before check-in day's local reference time.
    confirmation_lead: timedelta = timedelta(days=2)
    confirmation_local_time: time = time(11, 0)
    # How long to wait before re-evaluating an item that failed a time-based gate.
    retry_interval: timedelta = timedelta(hours=1)
    # Appointment confirmations (Cars24) go out this long before the slot [CD].
    appointment_lead: timedelta = timedelta(hours=18)


BookingShape = Literal["stay", "appointment"]


def booking_shape(event: BookingEvent) -> BookingShape:
    """The one owner of "what was booked": a stay at a property, or an appointment (D-036)."""
    has_stay = event.stay is not None and event.property is not None
    has_appointment = event.appointment is not None
    if has_stay == has_appointment:
        raise EventShapeError(
            f"event {event.event_id} must carry a stay or an appointment, not both or neither"
        )
    return "stay" if has_stay else "appointment"


def stay_of(event: BookingEvent) -> tuple[Property, Stay]:
    if booking_shape(event) != "stay" or event.property is None or event.stay is None:
        raise EventShapeError(f"event {event.event_id} has no stay")
    return event.property, event.stay


def appointment_of(event: BookingEvent) -> Appointment:
    if booking_shape(event) != "appointment" or event.appointment is None:
        raise EventShapeError(f"event {event.event_id} has no appointment")
    return event.appointment


@dataclass(frozen=True)
class JourneyPlan:
    purpose: Literal["J1", "J2"]
    due_at: datetime


def plan_journey(event: BookingEvent, now: datetime, rules: JourneyRules) -> JourneyPlan | None:
    """None means the event starts no journey (cancelled, out of purpose, or too late)."""
    if event.status in ("payment_failed", "payment_pending"):
        return _plan_j1(event, now, rules)
    if event.status == "confirmed":
        return _plan_j2(event, now, rules)
    return None


def _plan_j1(event: BookingEvent, now: datetime, rules: JourneyRules) -> JourneyPlan | None:
    if "J1" not in event.purposes_allowed:
        return None
    # After the payment date a BNPL booking can no longer be paid; a call would contradict the rule.
    if event.payment_due_at is not None and now >= event.payment_due_at:
        return None
    due = now
    if event.status == "payment_pending":
        due = max(now, event.occurred_at + rules.payment_pending_threshold)
    return JourneyPlan(purpose="J1", due_at=due)


def _plan_j2(event: BookingEvent, now: datetime, rules: JourneyRules) -> JourneyPlan | None:
    if "J2" not in event.purposes_allowed:
        return None
    if booking_shape(event) == "appointment":
        slot = appointment_of(event).slot_start
        if now >= slot:
            return None
        return JourneyPlan(purpose="J2", due_at=max(now, slot - rules.appointment_lead))
    _, stay = stay_of(event)
    check_in_local = datetime.combine(stay.check_in, rules.confirmation_local_time, _IST)
    if now >= check_in_local:
        return None
    return JourneyPlan(purpose="J2", due_at=max(now, check_in_local - rules.confirmation_lead))
