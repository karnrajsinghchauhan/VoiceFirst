"""One demo call on a fresh, isolated engine: real dispatcher, gates and agent; mock providers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select

from app.campaigns.seed_data import SeedPlan, seed_registry
from app.compliance.killswitch import engage
from app.compliance.models import DialAttemptRow
from app.contracts.generated.booking_event import BookingEvent
from app.core.bus import MemoryBus, Topic
from app.core.clock import FrozenClock
from app.core.config import Settings
from app.core.db import create_all, make_engine, make_session_factory, transaction
from app.core.errors import StateConflictError
from app.handoff.transfer import InMemoryHumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.registry import build_providers
from app.simulator.caller import Persona, ScriptedCaller
from app.telephony.handle import CallHandle
from app.voice.agent import HANDOFF_QUEUES, ConversationResult, Listener
from app.wiring.runtime import Runtime, build_dispatcher


@dataclass(frozen=True)
class Published:
    topic: str
    record: dict[str, object]
    t_ms: int


class TimedBus(MemoryBus):
    """Records when each message left the engine, so the timeline shows real engine time."""

    def __init__(self, started: float) -> None:
        super().__init__()
        self._started = started
        self.log: list[Published] = []

    def publish(self, topic: Topic, key: str, record: BaseModel) -> None:
        super().publish(topic, key, record)
        t_ms = round((time.perf_counter() - self._started) * 1000)
        self.log.append(Published(topic, self.messages[topic][-1][1], t_ms))


@dataclass
class EngineRun:
    event: BookingEvent
    bus: TimedBus
    runtime: Runtime
    dialled: bool
    queue_reason: str
    result: ConversationResult | None


def demo_settings() -> Settings:
    # An isolated in-memory store per run: the demo can never touch tenant data.
    return Settings(environment="test", database_url="sqlite://", bus="memory")


def _runtime(settings: Settings, bus: TimedBus, at: datetime) -> Runtime:
    engine = make_engine(settings.database_url, settings.tenant_id)
    create_all(engine)
    return Runtime(
        settings=settings,
        session_factory=make_session_factory(engine),
        bus=bus,
        clock=FrozenClock(at),
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        # One human free per queue, so the demo shows a real warm transfer with its summary.
        human_queue=InMemoryHumanQueue(available=dict.fromkeys(HANDOFF_QUEUES, 1)),
    )


def run_call(
    settings: Settings, event: BookingEvent, persona: Persona, at: datetime, killed: bool
) -> EngineRun:
    started = time.perf_counter()
    bus = TimedBus(started)
    rt = _runtime(settings, bus, at)
    with transaction(rt.session_factory) as s:
        plan = SeedPlan(events=(event,), dnd_phones=frozenset(), shared_phone="")
        seed_registry(s, settings, plan)
        if killed:
            engage(
                s,
                bus,
                rt.clock,
                tenant_id=settings.tenant_id,
                actor="demo",
                role="ops",
                reason="demo kill switch",
            )
    results: list[ConversationResult] = []

    def listener(_handle: CallHandle, ev: BookingEvent) -> Listener:
        return ScriptedCaller(persona, ev.customer.preferred_language, 0)

    dispatcher = build_dispatcher(rt, listener_factory=listener, on_result=results.append)
    dispatcher.ingest(event.model_dump(mode="json"))
    dispatched = dispatcher.run_due()
    with transaction(rt.session_factory) as s:
        dialled = s.scalar(select(DialAttemptRow.call_id).limit(1)) is not None
    reason = dispatched[0].reason if dispatched else "kill_switch_engaged"
    return EngineRun(
        event=event,
        bus=bus,
        runtime=rt,
        dialled=dialled,
        queue_reason=reason,
        result=results[0] if results else None,
    )


def time_kill_switch(settings: Settings, event: BookingEvent, at: datetime) -> int:
    """Engine time from engaging the switch to the dispatcher refusing a due dial."""
    rt = _runtime(settings, TimedBus(time.perf_counter()), at)
    with transaction(rt.session_factory) as s:
        seed_registry(
            s, settings, SeedPlan(events=(event,), dnd_phones=frozenset(), shared_phone="")
        )
    dispatcher = build_dispatcher(rt)
    dispatcher.ingest(event.model_dump(mode="json"))
    started = time.perf_counter()
    with transaction(rt.session_factory) as s:
        engage(
            s,
            rt.bus,
            rt.clock,
            tenant_id=settings.tenant_id,
            actor="demo",
            role="ops",
            reason="demo kill switch",
        )
    dispatched = dispatcher.run_due()
    elapsed = round((time.perf_counter() - started) * 1000)
    with transaction(rt.session_factory) as s:
        dialled = s.scalar(select(DialAttemptRow.call_id).limit(1)) is not None
    if dispatched or dialled:
        raise StateConflictError("the dispatcher dialled after the kill switch was engaged")
    return elapsed
