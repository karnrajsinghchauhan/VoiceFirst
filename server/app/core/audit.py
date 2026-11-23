"""Append-only audit log for every privileged action (2.7 baseline). Written to Postgres and av.audit.v1."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.contracts.generated.audit_event import AuditEvent
from app.core.bus import EventBus
from app.core.db import Base, UtcDateTime
from app.core.ids import new_id

Role = Literal["admin", "ops", "auditor", "read_only", "system"]


class AuditRow(Base):
    __tablename__ = "audit_log"
    audit_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String)
    trace_id: Mapped[str] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    actor: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)


def write_audit(
    session: Session,
    bus: EventBus,
    *,
    tenant_id: str,
    trace_id: str,
    at: datetime,
    actor: str,
    role: Role,
    action: str,
    target: str,
    reason: str,
) -> AuditEvent:
    event = AuditEvent(
        schema_version="1.0.0",
        tenant_id=tenant_id,
        trace_id=trace_id,
        audit_id=new_id("aud"),
        at=at,
        actor=actor,
        role=role,
        action=action,
        target=target,
        reason=reason,
    )
    session.add(
        AuditRow(
            audit_id=event.audit_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            at=at,
            actor=actor,
            role=role,
            action=action,
            target=target,
            reason=reason,
        )
    )
    session.flush()
    bus.publish("av.audit.v1", target, event)
    return event
