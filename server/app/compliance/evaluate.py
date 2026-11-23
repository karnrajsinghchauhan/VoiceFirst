"""compliance.evaluate(): the only constructor of GateClearance (9.1, 9.2).

Runs the gates in order and stops at the first failure. The gate_decision is
written (and published) in every case, before any dial can happen.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.compliance.clearance import GateClearance, mint
from app.compliance.context import CallPurpose, GateContext
from app.compliance.gates import GATES
from app.compliance.models import ClearanceRow, GateDecisionRow
from app.compliance.repository import load_context
from app.contracts.generated.booking_event import BookingEvent
from app.contracts.generated.gate_decision import Gate, GateDecision
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import GateError
from app.core.ids import new_id, phone_hash


def run_gates(ctx: GateContext) -> tuple[list[Gate], GateError | None]:
    """Pure. Returns the per-gate results and the first failure, if any."""
    results: list[Gate] = []
    failure: GateError | None = None
    for name, gate in GATES:
        if failure is not None:
            results.append(Gate(name=name, passed=False, reason_code="not_evaluated"))
            continue
        try:
            gate(ctx)
        except GateError as exc:
            failure = exc
            results.append(Gate(name=name, passed=False, reason_code=exc.code))
            continue
        results.append(Gate(name=name, passed=True, reason_code="ok"))
    return results, failure


def evaluate(
    session: Session,
    bus: EventBus,
    settings: Settings,
    clock: Clock,
    event: BookingEvent,
    purpose: CallPurpose,
    cli_e164: str,
) -> GateClearance:
    """Returns a single-use clearance or raises the first failing gate's typed error."""
    now = clock.now()
    ctx = load_context(session, settings, event, purpose, cli_e164, now)
    results, failure = run_gates(ctx)
    decision_id = new_id("gd")
    clearance_id = None if failure else new_id("clr")
    decision = GateDecision(
        schema_version="1.0.0",
        tenant_id=event.tenant_id,
        trace_id=event.trace_id,
        decision_id=decision_id,
        booking_event_id=event.event_id,
        phone_hash=phone_hash(event.customer.phone_e164, settings.phone_pepper),
        evaluated_at=now,
        gates=results,
        clearance_id=clearance_id,
    )
    session.add(
        GateDecisionRow(
            decision_id=decision_id,
            tenant_id=event.tenant_id,
            trace_id=event.trace_id,
            booking_event_id=event.event_id,
            booking_id=event.booking_id,
            purpose=purpose,
            phone_hash=decision.phone_hash,
            evaluated_at=now,
            gates=[g.model_dump() for g in results],
            clearance_id=clearance_id,
        )
    )
    session.flush()
    bus.publish("av.gate-decisions.v1", event.booking_id, decision)
    if failure is not None:
        raise failure
    assert clearance_id is not None
    expires_at = now + timedelta(seconds=settings.compliance.clearance_ttl_seconds)
    session.add(
        ClearanceRow(
            clearance_id=clearance_id,
            decision_id=decision_id,
            tenant_id=event.tenant_id,
            booking_event_id=event.event_id,
            booking_id=event.booking_id,
            phone_e164=event.customer.phone_e164,
            cli_e164=cli_e164,
            purpose=purpose,
            issued_at=now,
            expires_at=expires_at,
            consumed_at=None,
        )
    )
    session.flush()
    return mint(
        clearance_id=clearance_id,
        decision_id=decision_id,
        trace_id=event.trace_id,
        booking_event_id=event.event_id,
        booking_id=event.booking_id,
        phone_e164=event.customer.phone_e164,
        cli_e164=cli_e164,
        purpose=purpose,
        issued_at=now,
        expires_at=expires_at,
    )
