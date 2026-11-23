"""S6: the Numbers view shows each declared CLI with complaints, answer rate and auto-pause."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.stubs import build_stub_deps
from app.compliance.complaints import ingest_complaint
from app.contracts.generated.complaint import Complaint
from app.core.db import transaction
from app.core.ids import new_id, new_trace_id, sha256_hex
from tests.factories import SERVICE_CLI, seed_cli


def test_numbers_view(session_factory, settings, bus, clock):
    with transaction(session_factory) as s:
        seed_cli(s, settings)
        seed_cli(s, settings, cli_e164="+911601999888", series="1601", purpose="service")
        ingest_complaint(
            s,
            bus,
            settings,
            Complaint(
                schema_version="1.0.0",
                tenant_id=settings.tenant_id,
                trace_id=new_trace_id(),
                complaint_id=new_id("cmp"),
                cli_e164=SERVICE_CLI,
                complainant_hash=sha256_hex("a"),
                received_at=clock.now(),
                source="dlt_forwarded",
                ai_flagged=True,
                dlt_ref=None,
            ),
        )
    app = create_app(build_stub_deps(settings, session_factory, bus, clock))
    rows = TestClient(app).get("/numbers", headers={"Authorization": "Bearer dev-ro-token"}).json()
    by = {r["cli_e164"]: r for r in rows}
    paused = by[SERVICE_CLI]
    assert paused["complaints_10d"] == 1 and paused["auto_paused"] is True
    assert paused["series"] == "1600" and paused["declaration_ref"] == "DLT-A2P-0001"
    assert paused["answer_rate"] is None  # never dialled
    other = by["+911601999888"]
    assert other["auto_paused"] is False and other["status"] == "active"
