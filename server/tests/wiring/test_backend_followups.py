"""Review R1 C1/H5: a promised callback reaches a person, and a CRM outage cannot erase a handoff."""

from __future__ import annotations

from sqlalchemy import select

from app.core.db import transaction
from app.core.errors import ProviderError
from app.handoff.models import HandoffRow
from app.handoff.transfer import InMemoryHumanQueue
from app.incidents.models import IncidentRow
from app.providers.crm.mock import MockCrm
from app.providers.registry import build_providers
from app.wiring.backend import LiveToolBackend
from tests.factories import make_event
from tests.outcome_factory import make_summary


class DownCrm(MockCrm):
    def create_ticket(self, subject, body, requester_ref, tags, priority):  # type: ignore[no-untyped-def]
        raise ProviderError("crm unavailable")


def _backend(session_factory, bus, settings, clock, crm) -> LiveToolBackend:
    p = build_providers(settings)
    return LiveToolBackend(
        session_factory=session_factory,
        bus=bus,
        settings=settings,
        clock=clock,
        whatsapp_provider=p.whatsapp,
        crm=crm,
        telephony=p.telephony,
        human_queue=InMemoryHumanQueue(),
        provider_call_id="prov-1",
    )


def test_a_scheduled_callback_opens_a_crm_ticket(session_factory, bus, settings, clock):
    crm = MockCrm()
    backend = _backend(session_factory, bus, settings, clock, crm)
    result = backend.schedule_callback("call_1", make_event(settings), "booker busy", "shaam ko")
    ticket = crm.tickets[result.ref]  # type: ignore[index]
    assert "callback" in ticket["tags"] and "booker busy" in str(ticket["body"])


def test_a_crm_outage_keeps_the_handoff_and_pages_a_human(session_factory, bus, settings, clock):
    backend = _backend(session_factory, bus, settings, clock, DownCrm())
    summary = make_summary(clock.now())
    result = backend.warm_transfer(summary.call_id, make_event(settings), summary)
    assert result.queue == summary.queue
    with transaction(session_factory) as s:
        assert s.scalar(select(HandoffRow).where(HandoffRow.call_id == summary.call_id)) is not None
        pages = s.scalars(select(IncidentRow).where(IncidentRow.kind == "page")).all()
        assert any("crm_case_failed" in p.summary for p in pages)
