"""REQ-DPDP-06: breach detected_at recorded; Board report due within 72 h; principals notified without delay."""

from datetime import timedelta

import pytest

from app.core.errors import StateConflictError
from app.incidents.service import mark_principals_notified, mark_reported, open_incident, overdue


def test_72h_clock_starts_at_detection(session, settings, clock):
    detected = clock.now() - timedelta(hours=5)  # noticed now, detected five hours ago
    row = open_incident(
        session,
        tenant_id=settings.tenant_id,
        kind="dpdp_breach",
        severity="sev1",
        summary="test breach",
        detected_at=detected,
    )
    assert row.report_due_at == detected + timedelta(hours=72)
    assert (
        overdue(session, settings.tenant_id, detected + timedelta(hours=72) - timedelta(seconds=1))
        == []
    )
    assert [
        r.incident_id for r in overdue(session, settings.tenant_id, detected + timedelta(hours=72))
    ] == [row.incident_id]
    mark_reported(session, row.incident_id, detected + timedelta(hours=40))
    assert overdue(session, settings.tenant_id, detected + timedelta(hours=100)) == []


def test_principal_notification_is_recorded(session, settings, clock):
    row = open_incident(
        session,
        tenant_id=settings.tenant_id,
        kind="dpdp_breach",
        severity="sev1",
        summary="b",
        detected_at=clock.now(),
    )
    mark_principals_notified(session, row.incident_id, clock.now() + timedelta(minutes=30))
    assert row.principals_notified_at is not None


def test_only_breaches_notify_principals(session, settings, clock):
    row = open_incident(
        session,
        tenant_id=settings.tenant_id,
        kind="cert_in",
        severity="sev2",
        summary="c",
        detected_at=clock.now(),
    )
    with pytest.raises(StateConflictError):
        mark_principals_notified(session, row.incident_id, clock.now())
