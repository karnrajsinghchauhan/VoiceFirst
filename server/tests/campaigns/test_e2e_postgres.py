"""A campaign slice on real Postgres: savepoints, conditional clearance consumption, JSON columns."""

from __future__ import annotations

import os
from collections import Counter

import pytest
from sqlalchemy import select

from app.campaigns.seed_data import build_seed
from app.compliance.models import ClearanceRow, DialAttemptRow
from app.core.db import Base, create_all, make_engine, make_session_factory, transaction
from tests.campaigns.m4 import run_campaign

pytestmark = pytest.mark.e2e


@pytest.fixture
def pg_factory():
    url = os.environ["AV_TEST_DATABASE_URL"]
    engine = make_engine(url, "agoda-in")
    Base.metadata.drop_all(engine)
    create_all(engine)
    yield make_session_factory(engine)
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_campaign_slice_on_postgres(pg_factory, bus, settings, clock):
    plan = build_seed(settings, count=120, seed=5, now=clock.now())
    run = run_campaign(pg_factory, bus, settings, clock, plan, days=2)
    with transaction(pg_factory) as s:
        attempts = list(s.scalars(select(DialAttemptRow)))
        consumed = {c.clearance_id: c.consumed_at for c in s.scalars(select(ClearanceRow))}
    assert attempts and len(attempts) == len(run.telephony.placed)
    assert all(consumed[a.clearance_id] is not None for a in attempts)
    assert max(Counter(a.booking_event_id for a in attempts).values()) <= 2
