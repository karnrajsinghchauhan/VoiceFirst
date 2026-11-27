"""Review R2 H2: an overdue CERT-In or Board report pages a person once, and the clock can be stopped."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import transaction
from app.handoff.transfer import InMemoryHumanQueue
from app.incidents.models import IncidentRow
from app.incidents.service import open_incident
from app.incidents.watch import page_overdue
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.registry import build_providers
from app.wiring.main import Runtime, build_api


def _open_cert_in(session_factory, settings, clock) -> str:
    with transaction(session_factory) as s:
        row = open_incident(
            s,
            tenant_id=settings.tenant_id,
            kind="cert_in",
            severity="sev1",
            summary="suspicious login",
            detected_at=clock.now(),
        )
        return row.incident_id


def test_overdue_report_pages_once(session_factory, settings, clock):
    incident_id = _open_cert_in(session_factory, settings, clock)
    late = clock.now() + timedelta(hours=7)
    with transaction(session_factory) as s:
        assert page_overdue(s, settings.tenant_id, late) == 1
        assert page_overdue(s, settings.tenant_id, late) == 0
        pages = s.scalars(select(IncidentRow).where(IncidentRow.kind == "page")).all()
        assert len(pages) == 1 and incident_id in pages[0].summary


def test_marking_reported_stops_the_clock(session_factory, bus, settings, clock):
    incident_id = _open_cert_in(session_factory, settings, clock)
    rt = Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )
    client = TestClient(build_api(rt))
    r = client.post(
        f"/incidents/{incident_id}/reported",
        json={"reason": "CERT-In form filed, ref 123"},
        headers={"Authorization": "Bearer dev-ops-token"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "reported"
    with transaction(session_factory) as s:
        assert page_overdue(s, settings.tenant_id, clock.now() + timedelta(hours=7)) == 0
