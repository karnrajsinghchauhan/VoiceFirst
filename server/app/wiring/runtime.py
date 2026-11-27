"""The engine runtime: builds every service once from Settings at boot; bad config fails here."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.campaigns.dispatcher import Dispatcher
from app.campaigns.journeys import JourneyRules
from app.contracts.generated.booking_event import BookingEvent
from app.core.bus import EventBus, make_bus
from app.core.clock import Clock, SystemClock
from app.core.config import Settings
from app.core.db import assert_not_superuser, make_engine, make_session_factory
from app.core.errors import NotBuiltYetError
from app.handoff.transfer import HumanQueue, InMemoryHumanQueue
from app.messaging.fallback import WhatsAppFallback
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings, validate_postcall_for_production
from app.providers.registry import Providers, build_providers
from app.simulator.caller import ScriptedCaller, load_personas
from app.telephony.handle import CallHandle
from app.voice.agent import ConversationResult, Listener
from app.wiring.runner import AgentCallRunner, ListenerFactory


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    session_factory: sessionmaker[Session]
    bus: EventBus
    clock: Clock
    providers: Providers
    cipher: DataCipher
    human_queue: HumanQueue


def _human_queue(settings: Settings) -> HumanQueue:
    if settings.environment == "production":
        raise NotBuiltYetError("AV-CCAAS-1: CCaaS human-queue adapter")
    # Dev and test: nobody is available, so every handoff books a callback and says so (P2).
    return InMemoryHumanQueue()


def _listener_factory(settings: Settings) -> ListenerFactory:
    """The customer side of a call. Only the mock telephony path has one until M8."""
    if settings.telephony != "mock":
        raise NotBuiltYetError("AV-M8: LiveKit media path for real telephony")
    cooperative = next(p for p in load_personas() if p.id == "C-01")

    def make(handle: CallHandle, event: BookingEvent) -> Listener:
        return ScriptedCaller(cooperative, event.customer.preferred_language, 0)

    return make


def build_runtime(settings: Settings) -> Runtime:
    postcall = PostcallSettings()
    if settings.environment == "production":
        validate_postcall_for_production(postcall)
    engine = make_engine(settings.database_url, settings.tenant_id)
    if settings.environment == "production":
        assert_not_superuser(engine)
    return Runtime(
        settings=settings,
        session_factory=make_session_factory(engine),
        bus=make_bus(settings.bus, settings.kafka_bootstrap),
        clock=SystemClock(),
        providers=build_providers(settings),
        cipher=DataCipher(postcall.data_key),
        human_queue=_human_queue(settings),
    )


def build_dispatcher(
    rt: Runtime,
    listener_factory: ListenerFactory | None = None,
    on_result: Callable[[ConversationResult], None] | None = None,
) -> Dispatcher:
    """The live demo supplies its own scenario caller; every other caller takes the default."""
    p = rt.providers
    runner = AgentCallRunner(
        session_factory=rt.session_factory,
        bus=rt.bus,
        settings=rt.settings,
        clock=rt.clock,
        llm=p.llm,
        telephony=p.telephony,
        whatsapp_provider=p.whatsapp,
        crm=p.crm,
        human_queue=rt.human_queue,
        cipher=rt.cipher,
        listener_factory=listener_factory or _listener_factory(rt.settings),
        model_ids=p.model_ids(),
        on_result=on_result,
    )
    return Dispatcher(
        session_factory=rt.session_factory,
        bus=rt.bus,
        settings=rt.settings,
        clock=rt.clock,
        telephony=p.telephony,
        runner=runner,
        fallback=WhatsAppFallback(rt.session_factory, rt.settings, rt.clock, p.whatsapp),
        cli_by_purpose=rt.settings.compliance.cli_by_purpose,
        rules=JourneyRules(),
    )
