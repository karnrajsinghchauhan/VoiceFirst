"""Implements campaigns.dispatcher.FallbackSender with its own unit of work."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.contracts.generated.booking_event import BookingEvent
from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import transaction
from app.messaging.whatsapp import send_no_answer_fallback
from app.providers.base import WhatsAppProvider


class WhatsAppFallback:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
        clock: Clock,
        provider: WhatsAppProvider,
    ) -> None:
        self._factory = session_factory
        self._settings = settings
        self._clock = clock
        self._provider = provider

    def send_no_answer_fallback(self, event: BookingEvent) -> None:
        with transaction(self._factory) as session:
            send_no_answer_fallback(session, self._settings, self._clock, self._provider, event)
