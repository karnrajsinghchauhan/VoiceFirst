"""Incident records: pages to humans, DPDP breaches, CERT-In reportable incidents."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime

IncidentKind = Literal["page", "dpdp_breach", "cert_in"]


class IncidentRow(Base):
    __tablename__ = "incidents"
    incident_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[IncidentKind] = mapped_column(String)
    severity: Mapped[Literal["sev1", "sev2", "sev3"]] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(UtcDateTime)
    report_due_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    principals_notified_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
