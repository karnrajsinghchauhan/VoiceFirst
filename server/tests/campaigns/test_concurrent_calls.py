"""Review R3 C1 / D-033: dialled calls run concurrently, gates stay exact, nobody waits on hold."""

from __future__ import annotations

import threading
import time

from sqlalchemy import select

from app.campaigns.dispatcher import Dispatcher
from app.campaigns.journeys import JourneyRules
from app.campaigns.seed_data import build_seed, seed_registry
from app.compliance.models import DialAttemptRow
from app.core.db import transaction
from app.messaging.fallback import WhatsAppFallback
from app.providers.registry import build_providers
from tests.factories import make_settings
from tests.outcome_factory import make_outcome


class SlowRunner:
    """Holds each call open briefly and records how many were live at once."""

    def __init__(self, clock) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self.live = 0
        self.peak = 0

    def run(self, handle, event, purpose):  # type: ignore[no-untyped-def]
        with self._lock:
            self.live += 1
            self.peak = max(self.peak, self.live)
        time.sleep(0.05)
        with self._lock:
            self.live -= 1
        return make_outcome(self._clock.now(), outcome="details_confirmed")


def _dispatcher(session_factory, bus, clock, workers: int) -> tuple[Dispatcher, SlowRunner, object]:
    settings = make_settings(call_workers=workers)
    providers = build_providers(settings)
    runner = SlowRunner(clock)
    d = Dispatcher(
        session_factory=session_factory,
        bus=bus,
        settings=settings,
        clock=clock,
        telephony=providers.telephony,
        runner=runner,
        fallback=WhatsAppFallback(session_factory, settings, clock, providers.whatsapp),
        cli_by_purpose=settings.compliance.cli_by_purpose,
        rules=JourneyRules(),
        call_workers=workers,
    )
    return d, runner, settings


def _load(d: Dispatcher, settings, session_factory, clock) -> None:
    plan = build_seed(settings, count=40, seed=7, now=clock.now())
    with transaction(session_factory) as s:
        seed_registry(s, settings, plan)
    for event in plan.events:
        d.ingest(event.model_dump(mode="json"))


def test_calls_overlap_up_to_the_worker_limit(session_factory, bus, clock):
    d, runner, settings = _dispatcher(session_factory, bus, clock, workers=4)
    _load(d, settings, session_factory, clock)
    d.run_due()
    assert 1 < runner.peak <= 4


def test_cooldown_holds_under_concurrency(session_factory, bus, clock):
    # The seed shares one number across two bookings; gates run sequentially, so only one dials.
    d, _, settings = _dispatcher(session_factory, bus, clock, workers=4)
    _load(d, settings, session_factory, clock)
    d.run_due()
    phones: dict[str, int] = {}
    with transaction(session_factory) as s:
        for a in s.scalars(select(DialAttemptRow)):
            phones.setdefault(a.phone_hash, 0)
            phones[a.phone_hash] += 1
    assert phones, "nothing was dialled"
    assert max(phones.values()) == 1, "cooldown broke under concurrency: a number was dialled twice"
