"""Composition root. Builds every service once from Settings at boot; bad config fails here."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.api.app import create_app
from app.api.deps import ApiDeps, make_metrics
from app.campaigns.dispatcher import Dispatcher
from app.campaigns.journeys import JourneyRules
from app.campaigns.service import CampaignPort
from app.contracts.generated.booking_event import BookingEvent
from app.core.bus import EventBus, make_bus
from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.core.errors import NotBuiltYetError
from app.core.logging import configure_logging
from app.handoff.transfer import HumanQueue, InMemoryHumanQueue
from app.incidents.api_port import IncidentPort
from app.messaging.fallback import WhatsAppFallback
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings, validate_postcall_for_production
from app.providers.livekit_settings import LiveKitSettings
from app.providers.registry import Providers, build_providers
from app.rights.workflow import RightsSlaSettings
from app.simulator.caller import ScriptedCaller, load_personas
from app.telephony.handle import CallHandle
from app.voice.agent import Listener
from app.voice.livekit_bridge import LiveKitMediaBridge
from app.wiring.runner import AgentCallRunner, ListenerFactory
from app.wiring.simulator_port import ScenarioSimulator


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
    """The customer side of a call: the scripted caller on mock telephony, LiveKit otherwise."""
    if settings.telephony == "mock":
        cooperative = next(p for p in load_personas() if p.id == "C-01")

        def scripted(handle: CallHandle, event: BookingEvent) -> Listener:
            return ScriptedCaller(cooperative, event.customer.preferred_language, 0)

        return scripted
    # Raises ConfigError at boot when LiveKit keys are missing (D-502).
    bridge = LiveKitMediaBridge(settings, LiveKitSettings())

    def live(handle: CallHandle, event: BookingEvent) -> Listener:
        return bridge.listener_for(handle.provider_call_id, event.customer.preferred_language)

    return live


def build_runtime(settings: Settings) -> Runtime:
    postcall = PostcallSettings()
    if settings.environment == "production":
        validate_postcall_for_production(postcall)
    engine = make_engine(settings.database_url)
    return Runtime(
        settings=settings,
        session_factory=make_session_factory(engine),
        bus=make_bus(settings.bus, settings.kafka_bootstrap),
        clock=SystemClock(),
        providers=build_providers(settings),
        cipher=DataCipher(postcall.data_key),
        human_queue=_human_queue(settings),
    )


def build_api(rt: Runtime) -> FastAPI:
    return create_app(
        ApiDeps(
            settings=rt.settings,
            session_factory=rt.session_factory,
            bus=rt.bus,
            clock=rt.clock,
            cipher=rt.cipher,
            rights_sla=RightsSlaSettings(),
            simulator=ScenarioSimulator(rt.settings),
            campaigns=CampaignPort(rt.session_factory, rt.settings.tenant_id, rt.clock),
            incidents=IncidentPort(rt.session_factory, rt.settings.tenant_id),
            human_queue=rt.human_queue,
            crm=rt.providers.crm,
            metrics=make_metrics(),
        )
    )


def build_dispatcher(rt: Runtime) -> Dispatcher:
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
        listener_factory=_listener_factory(rt.settings),
        model_ids=p.model_ids(),
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


def api_app() -> FastAPI:
    """uvicorn entry point: `uvicorn app.wiring.main:api_app --factory`."""
    configure_logging()
    return build_api(build_runtime(get_settings()))
