"""The six /demo scenarios: which eval persona answers and which booking event starts the call."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.api.ports import DemoScenario
from app.campaigns.journeys import JourneyRules, stay_of
from app.compliance.holdout import is_held_out
from app.contracts.generated.booking_event import BookingEvent
from app.core.config import Settings
from app.core.errors import StateConflictError
from app.core.types import Purpose
from app.simulator.caller import Persona
from app.simulator.scenario import make_event

EventStatus = Literal["payment_failed", "payment_pending", "confirmed"]


@dataclass(frozen=True)
class ScenarioSpec:
    persona_id: str
    status: EventStatus
    purpose: Purpose


SCENARIOS: dict[DemoScenario, ScenarioSpec] = {
    "failed_upi": ScenarioSpec("C-01", "payment_failed", "J1"),
    "confirmation": ScenarioSpec("C-28", "confirmed", "J2"),
    "angry_refund": ScenarioSpec("C-05", "payment_failed", "J1"),
    "stop_calling": ScenarioSpec("C-10", "payment_pending", "J1"),
    "child_answers": ScenarioSpec("C-11", "payment_pending", "J1"),
    "card_number": ScenarioSpec("C-17", "payment_failed", "J1"),
    "cars24_inspection": ScenarioSpec("C-31", "confirmed", "J2"),
    "cars24_reschedule": ScenarioSpec("C-32", "confirmed", "J2"),
}

# The holdout is never overridden, so the demo picks the first seed whose booking is not held out.
_MAX_SEEDS = 50


def build_event(
    settings: Settings, spec: ScenarioSpec, persona: Persona, at: datetime
) -> BookingEvent:
    """A booking event that is due at `at`: J1 past its threshold, J2 two days before check-in."""
    for seed in range(_MAX_SEEDS):
        base = make_event(settings, persona, persona.preferred_language, seed)
        if not is_held_out(
            settings.holdout.experiment_salt, base.booking_id, settings.holdout.percent
        ):
            break
    else:
        raise StateConflictError("no demo seed outside the holdout; the bucket function is broken")
    if base.appointment is not None:
        # Due exactly now: the slot sits one appointment lead ahead (D-036).
        slot = at + JourneyRules().appointment_lead
        return base.model_copy(
            update={
                "status": spec.status,
                "occurred_at": at - timedelta(hours=3),
                "appointment": base.appointment.model_copy(update={"slot_start": slot}),
            }
        )
    check_in = (at + timedelta(days=2)).date()
    return base.model_copy(
        update={
            "status": spec.status,
            "occurred_at": at - timedelta(hours=3),
            "payment_due_at": at + timedelta(days=2),
            "stay": stay_of(base)[1].model_copy(
                update={"check_in": check_in, "check_out": check_in + timedelta(days=2)}
            ),
        }
    )
