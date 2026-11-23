"""Runs a seeded campaign through the real dispatcher with mock telephony and the stub runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.campaigns.dispatcher import Dispatcher, DispatchResult
from app.campaigns.journeys import JourneyRules
from app.campaigns.seed_data import SeedPlan, seed_registry
from app.core.bus import MemoryBus
from app.core.clock import FrozenClock
from app.core.config import Settings
from app.core.db import transaction
from app.providers.telephony.mock import MockTelephony
from tests.campaigns.stubs import RecordingFallback, StubRunner


@dataclass
class CampaignRun:
    results: list[DispatchResult]
    telephony: MockTelephony
    runner: StubRunner
    fallback: RecordingFallback


def run_campaign(
    factory: sessionmaker[Session],
    bus: MemoryBus,
    settings: Settings,
    clock: FrozenClock,
    plan: SeedPlan,
    *,
    days: int,
) -> CampaignRun:
    with transaction(factory) as session:
        seed_registry(session, settings, plan)
    run = CampaignRun([], MockTelephony(), StubRunner(clock), RecordingFallback())
    dispatcher = Dispatcher(
        session_factory=factory,
        bus=bus,
        settings=settings,
        clock=clock,
        telephony=run.telephony,
        runner=run.runner,
        fallback=run.fallback,
        cli_by_purpose=settings.compliance.cli_by_purpose,
        rules=JourneyRules(),
    )
    for event in plan.events:
        dispatcher.ingest(event.model_dump(mode="json"))
    # Hourly ticks, as a scheduler would run the dispatcher.
    for _ in range(days * 24):
        run.results.extend(dispatcher.run_due())
        clock.advance(timedelta(hours=1))
    return run
