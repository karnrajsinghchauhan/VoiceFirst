"""Which journey, if any, a booking event starts, and when. Pure functions of the event and the clock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from app.contracts.generated.booking_event import BookingEvent

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
    check_in_local = datetime.combine(event.stay.check_in, rules.confirmation_local_time, _IST)
    if now >= check_in_local:
        return None
    return JourneyPlan(purpose="J2", due_at=max(now, check_in_local - rules.confirmation_lead))
