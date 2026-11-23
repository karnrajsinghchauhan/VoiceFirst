"""`make seed`: 1,000 deterministic demo bookings ingested through the dispatcher into AV_DATABASE_URL.

Seeds the CLI registry, a transaction-basis consent per booking and purpose,
DND numbers and two opt-outs, then ingests every booking event. It does not
dial; run the dispatcher for that.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from typing import Literal

from app.campaigns.dispatcher import Dispatcher
from app.campaigns.journeys import JourneyRules
from app.campaigns.seed_data import build_seed, seed_registry
from app.compliance.consent import mark_dnc
from app.compliance.holdout import is_held_out
from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.call_outcome import CallOutcome
from app.core.bus import make_bus
from app.core.clock import FrozenClock
from app.core.config import get_settings
from app.core.db import create_all, make_engine, make_session_factory, transaction
from app.providers.telephony.mock import MockTelephony
from app.telephony.dial import CallHandle


class _NoCalls:
    """Seeding never dials; using either port here is a bug."""

    def run(
        self, handle: CallHandle, event: BookingEvent, purpose: Literal["J1", "J2"]
    ) -> CallOutcome:
        raise AssertionError("seed_demo does not place calls")

    def send_no_answer_fallback(self, event: BookingEvent) -> None:
        raise AssertionError("seed_demo does not send messages")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    settings = get_settings()
    engine = make_engine(settings.database_url)
    create_all(engine)
    factory = make_session_factory(engine)
    clock = FrozenClock(datetime(2026, 11, 23, 6, 30, tzinfo=UTC))
    plan = build_seed(settings, count=args.count, seed=args.seed, now=clock.now())
    with transaction(factory) as session:
        seed_registry(session, settings, plan)
        for event in plan.events[-2:]:
            mark_dnc(
                session,
                settings,
                phone_e164=event.customer.phone_e164,
                at=clock.now(),
                channel="voice",
                call_id=None,
            )
    no_calls = _NoCalls()
    dispatcher = Dispatcher(
        session_factory=factory,
        bus=make_bus(settings.bus, settings.kafka_bootstrap),
        settings=settings,
        clock=clock,
        telephony=MockTelephony(),
        runner=no_calls,
        fallback=no_calls,
        cli_by_purpose=settings.compliance.cli_by_purpose,
        rules=JourneyRules(),
    )
    for event in plan.events:
        dispatcher.ingest(event.model_dump(mode="json"))
    held = sum(
        is_held_out(settings.holdout.experiment_salt, e.booking_id, settings.holdout.percent)
        for e in plan.events
    )
    statuses = Counter(e.status for e in plan.events)
    cities = Counter(e.property.city for e in plan.events)
    print(f"seeded {len(plan.events)} bookings; holdout bucket {held}; statuses {dict(statuses)}")
    print(f"cities {dict(cities)}; DND numbers {len(plan.dnd_phones)}; opt-outs 2")


if __name__ == "__main__":
    main()
