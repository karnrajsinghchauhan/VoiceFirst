"""The production CallRunner: runs the agent on a placed call and records the outcome."""

from __future__ import annotations

import time
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.compliance.killswitch import is_engaged
from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.call_outcome import CallOutcome
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import transaction
from app.core.ids import phone_hash
from app.core.types import Purpose
from app.handoff.transfer import HumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.store import TranscriptTurn, record_outcome, store_transcript
from app.providers.base import CrmProvider, LlmProvider, TelephonyProvider, WhatsAppProvider
from app.telephony.handle import CallHandle
from app.voice.agent import CallSetup, Listener, run_conversation
from app.wiring.backend import LiveToolBackend

ListenerFactory = Callable[[CallHandle, BookingEvent], Listener]


class AgentCallRunner:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        bus: EventBus,
        settings: Settings,
        clock: Clock,
        llm: LlmProvider,
        telephony: TelephonyProvider,
        whatsapp_provider: WhatsAppProvider,
        crm: CrmProvider,
        human_queue: HumanQueue,
        cipher: DataCipher,
        listener_factory: ListenerFactory,
        model_ids: dict[str, str],
    ) -> None:
        self._factory = session_factory
        self._bus = bus
        self._settings = settings
        self._clock = clock
        self._llm = llm
        self._telephony = telephony
        self._wa = whatsapp_provider
        self._crm = crm
        self._queue = human_queue
        self._cipher = cipher
        self._listener_factory = listener_factory
        self._model_ids = model_ids

    def _killed(self) -> bool:
        with transaction(self._factory) as s:
            return is_engaged(s, self._settings.tenant_id)

    def run(self, handle: CallHandle, event: BookingEvent, purpose: Purpose) -> CallOutcome:
        backend = LiveToolBackend(
            session_factory=self._factory,
            bus=self._bus,
            settings=self._settings,
            clock=self._clock,
            whatsapp_provider=self._wa,
            crm=self._crm,
            telephony=self._telephony,
            human_queue=self._queue,
            provider_call_id=handle.provider_call_id,
        )
        result = run_conversation(
            CallSetup(
                event=event,
                purpose=purpose,
                call_id=handle.call_id,
                clearance_id=handle.clearance.clearance_id,
                cli=handle.clearance.cli_e164,
                settings=self._settings,
                clock=self._clock,
                llm=self._llm,
                backend=backend,
                listener=self._listener_factory(handle, event),
                is_killed=self._killed,
                monotonic=time.monotonic,
                model_ids=self._model_ids,
            )
        )
        ph = phone_hash(event.customer.phone_e164, self._settings.phone_pepper)
        with transaction(self._factory) as s:
            record_outcome(s, self._bus, result.outcome, ph)
            store_transcript(
                s,
                self._cipher,
                call_id=handle.call_id,
                phone_hash=ph,
                at=self._clock.now(),
                turns=[TranscriptTurn(t.speaker, t.text) for t in result.transcript],
            )
        return result.outcome
