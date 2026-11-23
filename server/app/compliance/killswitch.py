"""P5 kill switch state. One authenticated call engages it; the gate and telephony.dial both read it.

Dropping queued dials is the dispatcher's job (it re-evaluates every dial, and
the kill_switch gate fails); ending live calls is the call runner's job (it
checks `is_engaged` before every agent turn).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.compliance.models import KillSwitchRow
from app.compliance.repository import kill_switch_engaged
from app.core.audit import Role, write_audit
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.ids import new_trace_id


def _set(
    session: Session, bus: EventBus, clock: Clock, *, tenant_id: str, engaged: bool,
    actor: str, role: Role, reason: str,
) -> None:
    now = clock.now()
    session.merge(KillSwitchRow(tenant_id=tenant_id, engaged=engaged, actor=actor, reason=reason,
                                changed_at=now))
    session.flush()
    write_audit(session, bus, tenant_id=tenant_id, trace_id=new_trace_id(), at=now, actor=actor,
                role=role, action="kill_switch.engage" if engaged else "kill_switch.release",
                target=f"tenant:{tenant_id}", reason=reason)


def engage(
    session: Session, bus: EventBus, clock: Clock, *, tenant_id: str, actor: str, role: Role,
    reason: str,
) -> None:
    _set(session, bus, clock, tenant_id=tenant_id, engaged=True, actor=actor, role=role,
         reason=reason)


def release(
    session: Session, bus: EventBus, clock: Clock, *, tenant_id: str, actor: str, role: Role,
    reason: str,
) -> None:
    _set(session, bus, clock, tenant_id=tenant_id, engaged=False, actor=actor, role=role,
         reason=reason)


def is_engaged(session: Session, tenant_id: str) -> bool:
    return kill_switch_engaged(session, tenant_id)
