"""REQ-SEC-02: CERT-In report within 6 hours of noticing; the timer starts at detection."""

from datetime import timedelta

from app.incidents.service import open_incident, overdue


def test_six_hour_clock(session, settings, clock) -> None:
    detected = clock.now()
    clock.advance(timedelta(hours=1))  # the record is created an hour after detection
    row = open_incident(
        session,
        tenant_id=settings.tenant_id,
        kind="cert_in",
        severity="sev1",
        summary="suspicious login",
        detected_at=detected,
    )
    assert row.report_due_at == detected + timedelta(hours=6)
    assert overdue(session, settings.tenant_id, detected + timedelta(hours=5, minutes=59)) == []
    assert len(overdue(session, settings.tenant_id, detected + timedelta(hours=6))) == 1


def test_runbook_exists() -> None:
    from pathlib import Path

    text = (Path(__file__).parents[3] / "docs/runbooks/cert-in-incident.md").read_text()
    assert "6 hours" in text and "detected_at" in text
