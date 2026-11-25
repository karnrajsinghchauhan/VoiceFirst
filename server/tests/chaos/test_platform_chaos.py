"""11.11 platform chaos: telephony, WhatsApp, Redpanda (bus) and Postgres failures.

Expected every time: a loud error, no dial pre-dial, an alert where a human must act,
and never a silent degradation or a switch of provider.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.campaigns.models import QueueItemRow
from app.campaigns.seed_data import build_seed, seed_registry
from app.compliance.evaluate import evaluate
from app.compliance.models import ClearanceRow, DialAttemptRow, WhatsAppSendRow
from app.core.bus import Topic
from app.core.db import make_engine, make_session_factory, transaction
from app.core.errors import ProviderError
from app.handoff.transfer import InMemoryHumanQueue
from app.messaging.fallback import WhatsAppFallback
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.registry import build_providers
from app.providers.whatsapp.mock import MockWhatsApp
from app.wiring.main import Runtime, build_dispatcher
from tests.factories import SERVICE_CLI, make_event, seed_cli, seed_consent


class DownBus:
    """Redpanda unreachable: every publish fails, as KafkaBus does after its flush timeout."""

    def publish(self, topic: Topic, key: str, record: BaseModel) -> None:
        raise ProviderError(f"kafka publish to {topic} failed: timeout")


def _runtime(session_factory, bus, settings, clock) -> Runtime:
    return Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )


def _queue_one(rt: Runtime):
    plan = build_seed(rt.settings, count=40, seed=7, now=rt.clock.now())
    with transaction(rt.session_factory) as s:
        seed_registry(s, rt.settings, plan)
    dispatcher = build_dispatcher(rt)
    for event in plan.events:
        dispatcher.ingest(event.model_dump(mode="json"))
    return dispatcher


def test_telephony_down_pre_dial_raises_and_dials_nothing(session_factory, bus, settings, clock):
    rt = _runtime(session_factory, bus, settings, clock)
    dispatcher = _queue_one(rt)
    rt.providers.telephony.fail_next = True  # type: ignore[attr-defined]
    with pytest.raises(ProviderError):
        dispatcher.run_due()
    with transaction(session_factory) as s:
        assert s.scalars(select(DialAttemptRow)).all() == []
        assert (
            s.scalars(select(ClearanceRow).where(ClearanceRow.consumed_at.is_not(None))).all() == []
        )
        errored = s.scalars(select(QueueItemRow).where(QueueItemRow.state == "error")).all()
        assert len(errored) == 1 and errored[0].last_reason == "provider_error"


def test_bus_down_fails_closed_before_any_dial(session, settings, clock):
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    # The gate decision cannot be published, so no clearance is minted.
    with pytest.raises(ProviderError):
        evaluate(session, DownBus(), settings, clock, event, "J1", SERVICE_CLI)
    assert session.scalars(select(ClearanceRow)).all() == []


def test_postgres_down_raises_and_dials_nothing(settings, clock, bus):
    from app.providers.telephony.mock import MockTelephony

    dead = make_session_factory(
        make_engine(
            "postgresql+psycopg://postgres:postgres@127.0.0.1:1/none?connect_timeout=1", "agoda-in"
        )
    )
    event = make_event(settings)
    tel = MockTelephony()
    with pytest.raises(OperationalError), transaction(dead) as s:
        evaluate(s, bus, settings, clock, event, "J1", SERVICE_CLI)
    assert tel.placed == []


def test_whatsapp_down_for_fallback_raises_and_records_no_send(session_factory, settings, clock):
    wa = MockWhatsApp(fail_next=True)
    with pytest.raises(ProviderError):
        WhatsAppFallback(session_factory, settings, clock, wa).send_no_answer_fallback(
            make_event(settings)
        )
    with transaction(session_factory) as s:
        assert s.scalars(select(WhatsAppSendRow)).all() == []
