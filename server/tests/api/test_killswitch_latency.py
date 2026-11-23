"""P5: one authenticated call pauses all dialling within 5 s, audit-logged with actor and reason.

A background thread dials continuously through the real path (evaluate + dial)
while the main thread engages the kill switch over HTTP. Time is real: the
clock advances with the wall clock, anchored inside the call window so the test
does not depend on the hour it runs.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.api.app import create_app
from app.api.stubs import build_stub_deps
from app.compliance.evaluate import evaluate
from app.core.audit import AuditRow
from app.core.bus import MemoryBus
from app.core.db import create_all, make_session_factory, transaction
from app.core.errors import KillSwitchEngagedError
from app.providers.telephony.mock import MockTelephony
from app.telephony.dial import dial
from tests.api.conftest import OPS
from tests.factories import booking_id_with_holdout, make_event, seed_cli, seed_consent

DEADLINE_S = 5.0


class RealTimeClock:
    """Wall-clock elapsed time from a fixed in-window anchor (12:00 IST)."""

    def __init__(self) -> None:
        self._anchor = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)
        self._start = time.monotonic()

    def now(self) -> datetime:
        return self._anchor + timedelta(seconds=time.monotonic() - self._start)


def test_no_dial_within_5s_of_engage(settings, tmp_path):
    # A file database so the dial thread and the API thread hold separate connections.
    engine = create_engine(
        f"sqlite:///{tmp_path / 'ks.db'}", connect_args={"check_same_thread": False, "timeout": 10}
    )
    create_all(engine)
    factory = make_session_factory(engine)
    clock = RealTimeClock()
    bus = MemoryBus()
    with transaction(factory) as s:
        seed_cli(s, settings)
    tel = MockTelephony()
    stop = threading.Event()
    engaged_at: list[float] = []
    attempts: list[tuple[float, str]] = []  # (start time, "dialled" | "blocked")

    def dial_loop() -> None:
        n = 0
        while not stop.is_set():
            n += 1
            booking = booking_id_with_holdout(settings, False, start=n * 1000)
            event = make_event(
                settings, booking_id=booking, customer={"phone_e164": f"+9198{n:08d}"}
            )
            started = time.monotonic()
            try:
                with transaction(factory) as s:
                    seed_consent(s, settings, event)
                    clearance = evaluate(s, bus, settings, clock, event, "J1", "+911600123456")
                    dial(s, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
                attempts.append((started, "dialled"))
            except KillSwitchEngagedError:
                attempts.append((started, "blocked"))
                if engaged_at:
                    return
            time.sleep(0.01)

    worker = threading.Thread(target=dial_loop)
    worker.start()
    try:
        time.sleep(0.3)  # let some dials through first
        client = TestClient(create_app(build_stub_deps(settings, factory, bus, clock)))
        before = time.monotonic()
        response = client.post(
            "/killswitch", json={"engaged": True, "reason": "P5 drill"}, headers=OPS
        )
        engaged_at.append(time.monotonic())
        assert response.status_code == 200
        worker.join(timeout=DEADLINE_S)
    finally:
        stop.set()
        worker.join()

    assert any(outcome == "dialled" for _, outcome in attempts), "loop never dialled before engage"
    first_block = next(t for t, outcome in attempts if outcome == "blocked")
    assert first_block - before < DEADLINE_S
    # Nothing that started after the engage call returned was dialled.
    assert not [t for t, outcome in attempts if outcome == "dialled" and t > engaged_at[0]]
    with factory() as s:
        row = s.query(AuditRow).filter_by(action="kill_switch.engage").one()
        assert row.actor.startswith("ops:") and row.reason == "P5 drill"
    engine.dispose()
