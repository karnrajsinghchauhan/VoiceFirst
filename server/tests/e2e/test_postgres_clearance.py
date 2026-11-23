"""D-005: single-use clearance consumption behaves on Postgres as on SQLite, under concurrency."""

from __future__ import annotations

import os
import threading

import pytest

from app.compliance.evaluate import evaluate
from app.core.bus import MemoryBus
from app.core.db import Base, create_all, make_engine, make_session_factory, transaction
from app.core.errors import ClearanceInvalidError
from app.providers.telephony.mock import MockTelephony
from app.telephony.dial import dial
from tests.factories import SERVICE_CLI, make_event, seed_cli, seed_consent

pytestmark = pytest.mark.e2e


@pytest.fixture
def pg_factory():
    engine = make_engine(os.environ["AV_TEST_DATABASE_URL"])
    Base.metadata.drop_all(engine)
    create_all(engine)
    yield make_session_factory(engine)
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_concurrent_dials_consume_once(pg_factory, settings, clock):
    bus = MemoryBus()
    event = make_event(settings)
    with transaction(pg_factory) as s:
        seed_cli(s, settings)
        seed_consent(s, settings, event)
        clearance = evaluate(s, bus, settings, clock, event, "J1", SERVICE_CLI)
    tel = MockTelephony()
    barrier = threading.Barrier(4)
    outcomes: list[str] = []

    def attempt() -> None:
        barrier.wait()
        try:
            with transaction(pg_factory) as s:
                dial(s, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
            outcomes.append("dialled")
        except ClearanceInvalidError:
            outcomes.append("refused")

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["dialled", "refused", "refused", "refused"]
    assert len(tel.placed) == 1
