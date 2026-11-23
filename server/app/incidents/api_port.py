"""Implements app.api.ports.IncidentService over incidents.service.

The API speaks operator kinds; regulation speaks clocks. security -> CERT-In 6 h,
data_breach -> DPDP Board 72 h (CERT-In is opened alongside, because a breach is
also a reportable cyber incident), everything else -> a page.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.ports import IncidentKind, IncidentView
from app.core.db import transaction
from app.incidents.models import IncidentRow
from app.incidents.service import open_incident


def _view(row: IncidentRow, api_kind: IncidentKind, cert_in_due: datetime | None) -> IncidentView:
    status = "reported" if row.reported_at else ("closed" if row.acknowledged_at else "open")
    return IncidentView(
        incident_id=row.incident_id,
        kind=api_kind,
        summary=row.summary,
        detected_at=row.detected_at,
        cert_in_due_at=cert_in_due,
        board_report_due_at=row.report_due_at if row.kind == "dpdp_breach" else None,
        status=status,
    )


_API_KIND = {"cert_in": "security", "dpdp_breach": "data_breach", "page": "other"}


class IncidentPort:
    def __init__(self, session_factory: sessionmaker[Session], tenant_id: str) -> None:
        self._factory = session_factory
        self._tenant = tenant_id

    def list_incidents(self) -> list[IncidentView]:
        with transaction(self._factory) as session:
            rows = session.scalars(
                select(IncidentRow)
                .where(IncidentRow.tenant_id == self._tenant)
                .order_by(IncidentRow.detected_at)
            )
            return [
                _view(
                    r,
                    _API_KIND[r.kind],  # type: ignore[arg-type]
                    r.report_due_at if r.kind == "cert_in" else None,
                )
                for r in rows
            ]

    def open_incident(
        self, kind: IncidentKind, summary: str, detected_at: datetime, actor: str
    ) -> IncidentView:
        text = f"{summary} (opened by {actor})"
        with transaction(self._factory) as session:
            if kind == "security":
                row = open_incident(
                    session,
                    tenant_id=self._tenant,
                    kind="cert_in",
                    severity="sev1",
                    summary=text,
                    detected_at=detected_at,
                )
                return _view(row, kind, row.report_due_at)
            if kind == "data_breach":
                cert = open_incident(
                    session,
                    tenant_id=self._tenant,
                    kind="cert_in",
                    severity="sev1",
                    summary=text,
                    detected_at=detected_at,
                )
                row = open_incident(
                    session,
                    tenant_id=self._tenant,
                    kind="dpdp_breach",
                    severity="sev1",
                    summary=text,
                    detected_at=detected_at,
                )
                return _view(row, kind, cert.report_due_at)
            row = open_incident(
                session,
                tenant_id=self._tenant,
                kind="page",
                severity="sev2",
                summary=text,
                detected_at=detected_at,
            )
            return _view(row, kind, None)
