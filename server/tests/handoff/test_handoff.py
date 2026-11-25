from datetime import timedelta

import pytest

from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.errors import StateConflictError
from app.handoff import transfer
from app.handoff.models import CallbackRow
from app.handoff.summary import MAX_LINES, render_lines
from app.handoff.transfer import InMemoryHumanQueue, warm_transfer
from tests.outcome_factory import make_summary


def test_summary_is_at_most_five_lines_and_masks_booking(clock):
    summary = make_summary(clock.now())
    lines = render_lines(summary)
    assert len(lines) <= MAX_LINES
    assert summary.booking_masked == "******1234"
    assert all("BK0000" not in line for line in lines)
    HandoffSummary.model_validate(summary.model_dump())


def test_transfer_when_human_available(session, bus, clock):
    queue = InMemoryHumanQueue(available={"payments": 1})
    summary = make_summary(clock.now())
    result = warm_transfer(session, bus, queue, clock, summary, "female")
    assert result.kind == "transferred" and result.agent_ref
    assert "jod rahi hoon" in result.spoken_line
    assert bus.messages["av.handoffs.v1"][0][0] == summary.call_id
    assert session.query(CallbackRow).count() == 0


def test_no_human_schedules_callback_and_says_so(session, bus, clock):
    summary = make_summary(clock.now())
    result = warm_transfer(session, bus, InMemoryHumanQueue(), clock, summary, "male")
    assert result.kind == "callback_scheduled"
    assert "uplabdh nahi" in result.spoken_line and "kar raha hoon" in result.spoken_line
    assert result.callback_due_at == clock.now() + transfer.CALLBACK_DELAY
    assert session.query(CallbackRow).one().call_id == summary.call_id


def test_handoff_happens_once(session, bus, clock):
    summary = make_summary(clock.now())
    warm_transfer(session, bus, InMemoryHumanQueue(), clock, summary, "female")
    with pytest.raises(StateConflictError):
        warm_transfer(session, bus, InMemoryHumanQueue(), clock, summary, "female")


def test_ack_and_resolve_lifecycle(session, bus, clock):
    summary = make_summary(clock.now())
    warm_transfer(session, bus, InMemoryHumanQueue(), clock, summary, "female")
    transfer.acknowledge(session, summary.call_id, clock.now())
    with pytest.raises(StateConflictError):
        transfer.acknowledge(session, summary.call_id, clock.now())
    transfer.resolve(session, summary.call_id, clock.now() + timedelta(days=1))
    assert transfer.list_open(session, 10) == []
