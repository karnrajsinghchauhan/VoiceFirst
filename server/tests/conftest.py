"""Shared fixtures. Every test gets a fresh in-memory database, a memory bus and a frozen clock."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.bus import MemoryBus
from app.core.clock import FrozenClock
from app.core.config import Settings
from app.core.db import create_all, make_engine, make_session_factory
from tests.factories import make_settings


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def clock() -> FrozenClock:
    # 12:00 IST on 23 Nov 2026: inside the call window.
    return FrozenClock(datetime(2026, 11, 23, 6, 30, tzinfo=UTC))


@pytest.fixture
def bus() -> MemoryBus:
    return MemoryBus()


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = make_engine("sqlite://")
    create_all(engine)
    yield make_session_factory(engine)
    engine.dispose()


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    s = session_factory()
    yield s
    s.rollback()
    s.close()


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "e2e: needs Postgres (make e2e)")
