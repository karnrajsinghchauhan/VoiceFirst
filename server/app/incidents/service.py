"""Opening incidents and their regulatory clocks.

- page: a human must look now (complaint guardrail, WhatsApp quality drop, chaos alerts).
- dpdp_breach: detailed Board report due within 72 h of detection; principals
  notified "without delay" (REQ-DPDP-06).
- cert_in: report due within 6 h of noticing (REQ-SEC-02). Both timers start at
  detected_at, never at creation of the record.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, StateConflictError
from app.core.ids import new_id
from app.core.logging import get_logger
from app.incidents.models import IncidentKind, IncidentRow

Severity = Literal["sev1", "sev2", "sev3"]

REPORT_WINDOW: dict[IncidentKind, timedelta | None] = {
    "page": None,
    "dpdp_breach": timedelta(hours=72),
    "cert_in": timedelta(hours=6),
}

_log = get_logger(__name__)


def open_incident(
    session: Session,
    *,
    tenant_id: str,
    kind: IncidentKind,
    severity: Severity,
    summary: str,
    detected_at: datetime,
) -> IncidentRow:
    window = REPORT_WINDOW[kind]
    row = IncidentRow(
        incident_id=new_id("inc"),
        tenant_id=tenant_id,
        kind=kind,
        severity=severity,
        summary=summary,
        detected_at=detected_at,
        report_due_at=detected_at + window if window else None,
        reported_at=None,
        principals_notified_at=None,
        acknowledged_at=None,
        acknowledged_by=None,
    )
    session.add(row)
    session.flush()
    # The log line is the alert hook: Alertmanager pages on level=error with alert=true.
    _log.error(
        "incident opened",
        extra={"alert": True, "incident_id": row.incident_id, "kind": kind, "severity": severity},
    )
    return row


def page_human(
    session: Session, *, tenant_id: str, summary: str, at: datetime, severity: Severity = "sev2"
) -> IncidentRow:
    return open_incident(
        session,
        tenant_id=tenant_id,
        kind="page",
        severity=severity,
        summary=summary,
        detected_at=at,
    )


def _get(session: Session, incident_id: str) -> IncidentRow:
    row = session.get(IncidentRow, incident_id)
    if row is None:
        raise NotFoundError(f"incident {incident_id} not found")
    return row


def mark_reported(session: Session, incident_id: str, at: datetime) -> IncidentRow:
    row = _get(session, incident_id)
    if row.report_due_at is None:
        raise StateConflictError("this incident kind has no regulatory report")
    row.reported_at = at
    session.flush()
    return row


def mark_principals_notified(session: Session, incident_id: str, at: datetime) -> IncidentRow:
    row = _get(session, incident_id)
    if row.kind != "dpdp_breach":
        raise StateConflictError("only DPDP breaches notify data principals")
    row.principals_notified_at = at
    session.flush()
    return row


def acknowledge(session: Session, incident_id: str, at: datetime, actor: str) -> IncidentRow:
    row = _get(session, incident_id)
    row.acknowledged_at = at
    row.acknowledged_by = actor
    session.flush()
    return row


def overdue(session: Session, tenant_id: str, now: datetime) -> list[IncidentRow]:
    """Incidents whose regulatory report is due and not yet made."""
    stmt = select(IncidentRow).where(
        IncidentRow.tenant_id == tenant_id,
        IncidentRow.report_due_at.is_not(None),
        IncidentRow.reported_at.is_(None),
        IncidentRow.report_due_at <= now,
    )
    return list(session.scalars(stmt))


def list_open(session: Session, tenant_id: str) -> list[IncidentRow]:
    stmt = (
        select(IncidentRow)
        .where(IncidentRow.tenant_id == tenant_id, IncidentRow.acknowledged_at.is_(None))
        .order_by(IncidentRow.detected_at)
    )
    return list(session.scalars(stmt))
