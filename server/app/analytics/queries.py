"""Loads analytics inputs from the campaign tables. Intention-to-treat (D-202).

Population: every booking that got a J1 queue item. Group: the holdout bucket
function, not the holdout_members table, so bookings recovered before any gate
ran are still assigned to the right arm. Recovered: a later `confirmed` event
for the booking.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.lift import LiftResult, two_proportion_lift
from app.campaigns.models import BookingEventRow, QueueItemRow
from app.compliance.holdout import is_held_out
from app.core.config import Settings


@dataclass(frozen=True)
class ArmCounts:
    recovered_treated: int
    n_treated: int
    recovered_control: int
    n_control: int


def j1_arm_counts(session: Session, settings: Settings) -> ArmCounts:
    tenant = settings.tenant_id
    j1_bookings = set(
        session.scalars(
            select(QueueItemRow.booking_id).where(
                QueueItemRow.tenant_id == tenant, QueueItemRow.purpose == "J1"
            )
        )
    )
    confirmed = set(
        session.scalars(
            select(BookingEventRow.booking_id).where(
                BookingEventRow.tenant_id == tenant, BookingEventRow.status == "confirmed"
            )
        )
    )
    counts = {True: [0, 0], False: [0, 0]}
    for booking_id in j1_bookings:
        arm = is_held_out(settings.holdout.experiment_salt, booking_id, settings.holdout.percent)
        counts[arm][1] += 1
        counts[arm][0] += booking_id in confirmed
    return ArmCounts(
        recovered_treated=counts[False][0],
        n_treated=counts[False][1],
        recovered_control=counts[True][0],
        n_control=counts[True][1],
    )


def j1_lift(session: Session, settings: Settings) -> LiftResult:
    c = j1_arm_counts(session, settings)
    return two_proportion_lift(c.recovered_treated, c.n_treated, c.recovered_control, c.n_control)
