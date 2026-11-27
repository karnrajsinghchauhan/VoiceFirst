"""GET /status reports live checks and never leaks data."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.compliance.killswitch import engage
from app.core.db import transaction
from app.handoff.transfer import InMemoryHumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.registry import build_providers
from app.wiring.main import Runtime, build_api


def _client(session_factory, bus, settings, clock) -> TestClient:
    rt = Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )
    return TestClient(build_api(rt))


def test_status_is_operational_on_a_healthy_engine(session_factory, bus, settings, clock):
    body = _client(session_factory, bus, settings, clock).get("/status").json()
    assert body["overall"] == "operational"
    names = [c["name"] for c in body["components"]]
    assert "Database" in names and any("test doubles" in n for n in names)
    assert body["history"] == []


def test_status_shows_the_kill_switch_as_degraded(session_factory, bus, settings, clock):
    with transaction(session_factory) as s:
        engage(s, bus, clock, tenant_id=settings.tenant_id, actor="ops", role="ops", reason="drill")
    body = _client(session_factory, bus, settings, clock).get("/status").json()
    assert body["overall"] == "degraded"
    assert any("kill switch engaged" in c["name"] for c in body["components"])
