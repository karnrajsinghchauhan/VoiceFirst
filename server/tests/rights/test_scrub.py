"""Review R2 H1: erasure and the nightly purge remove names and numbers outside transcripts."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.campaigns.models import BookingEventRow
from app.campaigns.seed_data import build_seed, seed_registry
from app.compliance.models import ClearanceRow, DialAttemptRow
from app.core.db import transaction
from app.core.ids import phone_hash
from app.handoff.transfer import InMemoryHumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.registry import build_providers
from app.rights.scrub import ERASED, erase_for_phone, scrub_older_than
from app.wiring.runtime import Runtime, build_dispatcher


def _dial_some(session_factory, bus, settings, clock) -> None:
    rt = Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )
    plan = build_seed(settings, count=20, seed=7, now=clock.now())
    with transaction(session_factory) as s:
        seed_registry(s, settings, plan)
    dispatcher = build_dispatcher(rt)
    for event in plan.events:
        dispatcher.ingest(event.model_dump(mode="json"))
    for _ in range(6):
        dispatcher.run_due()
        clock.advance(timedelta(hours=1))


def test_erasure_scrubs_events_and_clearances_for_that_number(
    session_factory, bus, settings, clock
):
    _dial_some(session_factory, bus, settings, clock)
    with transaction(session_factory) as s:
        clearance = s.scalars(select(ClearanceRow)).first()
        assert clearance is not None, "no call was cleared"
        phone = clearance.phone_e164
        counts = erase_for_phone(s, phone, phone_hash(phone, settings.phone_pepper), clock.now())
        assert counts.booking_events >= 1 and counts.clearances >= 1
        phones = [e.payload["customer"]["phone_e164"] for e in s.scalars(select(BookingEventRow))]
        assert phone not in phones
        assert phone not in [c.phone_e164 for c in s.scalars(select(ClearanceRow))]


def test_purge_scrubs_everything_older_than_the_cutoff(session_factory, bus, settings, clock):
    _dial_some(session_factory, bus, settings, clock)
    with transaction(session_factory) as s:
        assert s.scalars(select(DialAttemptRow)).first() is not None
        scrub_older_than(s, clock.now() + timedelta(days=1))
        assert {
            e.payload["customer"]["first_name"] for e in s.scalars(select(BookingEventRow))
        } == {ERASED}
        assert {c.phone_e164 for c in s.scalars(select(ClearanceRow))} == {ERASED}
