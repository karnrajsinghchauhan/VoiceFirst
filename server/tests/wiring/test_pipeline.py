"""The integrated pilot path through app.wiring: event -> gates -> dial -> agent -> tools -> post-call."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.campaigns.seed_data import build_seed, seed_registry
from app.compliance.killswitch import engage
from app.compliance.models import DialAttemptRow, WhatsAppSendRow
from app.core.db import transaction
from app.handoff.transfer import InMemoryHumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.models import CallOutcomeRow
from app.postcall.settings import PostcallSettings
from app.postcall.store import read_transcript
from app.providers.registry import build_providers
from app.wiring.main import Runtime, build_api, build_dispatcher


def _runtime(session_factory, bus, settings, clock) -> Runtime:
    return Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )


def _run(rt: Runtime, count: int, hours: int) -> None:
    plan = build_seed(rt.settings, count=count, seed=7, now=rt.clock.now())
    with transaction(rt.session_factory) as s:
        seed_registry(s, rt.settings, plan)
    dispatcher = build_dispatcher(rt)
    for event in plan.events:
        dispatcher.ingest(event.model_dump(mode="json"))
    for _ in range(hours):
        dispatcher.run_due()
        rt.clock.advance(timedelta(hours=1))  # type: ignore[attr-defined]


def test_every_dial_ends_in_a_recorded_outcome_and_encrypted_transcript(
    session_factory, bus, settings, clock
):
    rt = _runtime(session_factory, bus, settings, clock)
    _run(rt, count=40, hours=8)
    with transaction(session_factory) as s:
        dials = s.scalars(select(DialAttemptRow)).all()
        outcomes = {r.call_id: r for r in s.scalars(select(CallOutcomeRow))}
        assert dials, "the seed produced no dialable bookings"
        assert {d.call_id for d in dials} == set(outcomes)
        for d in dials:
            turns = read_transcript(s, rt.cipher, d.call_id)
            assert turns and turns[0].speaker == "agent"
            assert "AI" in turns[0].text
            assert all("+91" not in t.text for t in turns)
        links = s.scalars(select(WhatsAppSendRow).where(WhatsAppSendRow.kind == "in_call")).all()
        assert links, "the cooperative caller never received a payment link"
    assert len(rt.providers.telephony.hung_up) == len(dials)  # type: ignore[attr-defined]
    assert len(bus.messages["av.call-outcomes.v1"]) == len(dials)


def test_kill_switch_stops_the_pipeline(session_factory, bus, settings, clock):
    rt = _runtime(session_factory, bus, settings, clock)
    with transaction(session_factory) as s:
        engage(s, bus, clock, tenant_id=settings.tenant_id, actor="ops", role="ops", reason="drill")
    _run(rt, count=40, hours=4)
    with transaction(session_factory) as s:
        assert s.scalars(select(DialAttemptRow)).all() == []


def test_api_simulate_runs_a_real_conversation(session_factory, bus, settings, clock):
    from fastapi.testclient import TestClient

    client = TestClient(build_api(_runtime(session_factory, bus, settings, clock)))
    r = client.post(
        "/simulate",
        json={"persona": "C-17", "seed": 1, "purpose": "J1"},
        headers={"Authorization": "Bearer dev-ops-token"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assertions_passed"] is True
    assert "AI" in body["transcript"][0]["text"]
    assert all("4111" not in line["text"] for line in body["transcript"])
