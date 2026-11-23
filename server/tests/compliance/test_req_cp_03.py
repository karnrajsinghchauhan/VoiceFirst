"""REQ-CP-03: every outcome carries the grievance channel; case SLAs mirror 48 h ack and 30-day resolution."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.crm.cases import open_case
from app.handoff import transfer
from app.handoff.transfer import InMemoryHumanQueue, warm_transfer
from app.providers.crm.mock import MockCrm
from tests.outcome_factory import make_outcome, make_summary


def test_outcome_without_grievance_channel_is_rejected(clock):
    with pytest.raises(ValidationError):
        make_outcome(clock.now(), grievance_channel="")


def test_sla_fields_are_48h_and_30d(clock):
    summary = make_summary(clock.now())
    assert summary.sla_ack_due_at - clock.now() == timedelta(hours=48)
    assert summary.sla_resolve_due_at - clock.now() == timedelta(days=30)


def test_case_body_carries_grievance_channel(clock, settings):
    crm = MockCrm()
    ticket = open_case(crm, make_summary(clock.now()), settings.grievance.channel)
    assert settings.grievance.channel in str(crm.tickets[ticket.ticket_id]["body"])


def test_sla_breaches_detected(session, bus, clock):
    summary = make_summary(clock.now())
    warm_transfer(session, bus, InMemoryHumanQueue(), clock, summary, "female")
    just_before = clock.now() + timedelta(hours=48) - timedelta(seconds=1)
    assert transfer.sla_breaches(session, just_before).unacknowledged == []
    at_ack = clock.now() + timedelta(hours=48)
    assert transfer.sla_breaches(session, at_ack).unacknowledged == [summary.call_id]
    transfer.acknowledge(session, summary.call_id, at_ack)
    late = clock.now() + timedelta(days=30)
    breaches = transfer.sla_breaches(session, late)
    assert breaches.unacknowledged == [] and breaches.unresolved == [summary.call_id]
