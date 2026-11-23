"""REQ-DPDP-05: rights requests (access, correction, erasure) run through a workflow with SLA timers."""

from datetime import timedelta

import pytest

from app.compliance.consent import consents_for, record_consent
from app.core.audit import AuditRow
from app.core.errors import StateConflictError
from app.core.ids import phone_hash
from app.postcall.crypto import DataCipher
from app.postcall.models import CallOutcomeRow, TranscriptRow
from app.postcall.settings import DEV_DATA_KEY
from app.postcall.store import TranscriptTurn, record_outcome, store_transcript
from app.rights import workflow
from app.rights.workflow import Actor, RightsSlaSettings
from tests.factories import PHONE
from tests.outcome_factory import make_outcome

ADMIN = Actor(actor="admin:test", role="admin")
CIPHER = DataCipher(DEV_DATA_KEY)


def _seed_call(session, bus, settings, clock):
    ph = phone_hash(PHONE, settings.phone_pepper)
    outcome = make_outcome(clock.now())
    record_outcome(session, bus, outcome, ph)
    store_transcript(
        session,
        CIPHER,
        tenant_id="agoda-in",
        call_id=outcome.call_id,
        phone_hash=ph,
        at=clock.now(),
        turns=[TranscriptTurn("customer", "haan bhej do")],
    )
    record_consent(
        session,
        settings,
        phone_e164=PHONE,
        basis="explicit",
        purpose="J1",
        channel="voice",
        obtained_at=clock.now(),
        booking_id=None,
        source_ref="call",
        trace_id="0" * 32,
    )
    return outcome


def _open(session, bus, settings, clock, kind):
    return workflow.open_request(
        session,
        bus,
        settings,
        RightsSlaSettings(),
        phone_e164=PHONE,
        kind=kind,
        at=clock.now(),
        actor=ADMIN,
    )


def test_sla_timers_and_overdue(session, bus, settings, clock):
    row = _open(session, bus, settings, clock, "access")
    assert row.ack_due_at - clock.now() == timedelta(hours=48)
    assert row.due_at - clock.now() == timedelta(days=30)
    assert workflow.overdue(session, clock.now()).unacknowledged == []
    late_ack = clock.now() + timedelta(hours=48)
    assert workflow.overdue(session, late_ack).unacknowledged == [row.request_id]
    workflow.acknowledge(
        session, bus, settings, request_id=row.request_id, at=late_ack, actor=ADMIN
    )
    late = clock.now() + timedelta(days=30)
    od = workflow.overdue(session, late)
    assert od.unacknowledged == [] and od.unresolved == [row.request_id]


def test_access_exports_principal_data(session, bus, settings, clock):
    outcome = _seed_call(session, bus, settings, clock)
    row = _open(session, bus, settings, clock, "access")
    export = workflow.fulfil_access(
        session,
        bus,
        settings,
        CIPHER,
        request_id=row.request_id,
        phone_e164=PHONE,
        at=clock.now(),
        actor=ADMIN,
    )
    assert export["calls"][0]["call_id"] == outcome.call_id
    assert export["transcripts"][outcome.call_id][0]["text"] == "haan bhej do"
    assert len(export["consents"]) == 1
    assert row.status == "completed"
    assert workflow.overdue(session, clock.now() + timedelta(days=60)).unresolved == []


def test_erasure_removes_transcripts_pseudonymises_outcomes_keeps_consent(
    session, bus, settings, clock
):
    outcome = _seed_call(session, bus, settings, clock)
    row = _open(session, bus, settings, clock, "erasure")
    counts = workflow.fulfil_erasure(
        session,
        bus,
        settings,
        request_id=row.request_id,
        phone_e164=PHONE,
        at=clock.now(),
        actor=ADMIN,
    )
    assert (counts.transcripts, counts.outcomes_pseudonymised) == (1, 1)
    assert session.query(TranscriptRow).count() == 0
    kept = session.get(CallOutcomeRow, outcome.call_id)
    assert kept.phone_hash == workflow.ERASED
    assert kept.booking_id.startswith("erased-") and kept.payload["booking_id"] == kept.booking_id
    assert len(consents_for(session, PHONE)) == 1  # retained as legal evidence [CD]


def test_every_step_is_audited(session, bus, settings, clock):
    row = _open(session, bus, settings, clock, "correction")
    workflow.fulfil_correction(
        session,
        bus,
        settings,
        request_id=row.request_id,
        phone_e164=PHONE,
        at=clock.now(),
        actor=ADMIN,
        note="name spelling",
    )
    actions = [a.action for a in session.query(AuditRow).order_by(AuditRow.at)]
    assert actions == ["rights.open", "rights.correction"]
    assert row.result["routed_to"] == "agoda_booking_record_owner"


def test_wrong_phone_or_kind_conflicts(session, bus, settings, clock):
    row = _open(session, bus, settings, clock, "erasure")
    with pytest.raises(StateConflictError):
        workflow.fulfil_erasure(
            session,
            bus,
            settings,
            request_id=row.request_id,
            phone_e164="+919000000000",
            at=clock.now(),
            actor=ADMIN,
        )
    with pytest.raises(StateConflictError):
        workflow.fulfil_correction(
            session,
            bus,
            settings,
            request_id=row.request_id,
            phone_e164=PHONE,
            at=clock.now(),
            actor=ADMIN,
            note="",
        )


def test_cannot_complete_twice(session, bus, settings, clock):
    row = _open(session, bus, settings, clock, "erasure")
    workflow.fulfil_erasure(
        session,
        bus,
        settings,
        request_id=row.request_id,
        phone_e164=PHONE,
        at=clock.now(),
        actor=ADMIN,
    )
    with pytest.raises(StateConflictError):
        workflow.fulfil_erasure(
            session,
            bus,
            settings,
            request_id=row.request_id,
            phone_e164=PHONE,
            at=clock.now(),
            actor=ADMIN,
        )
