"""S10: every /demo scenario runs the real engine; the kill switch stops dials in under 5 s."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.handoff.transfer import InMemoryHumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.registry import build_providers
from app.wiring.main import Runtime, build_api

PASSCODE = "test-demo-passcode"
HEADERS = {"x-demo-passcode": PASSCODE}

EXPECTED = {
    "failed_upi": "link_sent",
    "confirmation": "details_confirmed",
    "angry_refund": "handed_off",
    "stop_calling": "opted_out",
    "child_answers": "minor_on_line",
    "card_number": "link_sent",
}


@pytest.fixture
def client(session_factory, bus, settings, clock, monkeypatch) -> TestClient:
    monkeypatch.setenv("AV_DEMO_PASSCODE", PASSCODE)
    rt = Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )
    return TestClient(build_api(rt))


def _run(client: TestClient, scenario: str) -> dict:
    r = client.post("/demo/run", json={"scenario": scenario}, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("scenario", sorted(EXPECTED))
def test_each_scenario_runs_through_gates_and_the_agent(client, scenario):
    run = _run(client, scenario)
    kinds = [e["kind"] for e in run["events"]]
    assert kinds[0] == "holdout"
    assert kinds.count("gate") == 10 and "clearance" in kinds
    assert all(e["status"] == "pass" for e in run["events"] if e["kind"] in ("holdout", "gate"))
    assert run["events"][-1]["detail"]["outcome"] == EXPECTED[scenario]
    assert "AI" in run["transcript"][0]["text"]
    assert run["qa"]["score"] == 100, [c for c in run["qa"]["checks"] if not c["passed"]]
    assert run["cost_paise"]["total"] > 0


def test_link_scenarios_carry_a_whatsapp_preview(client):
    run = _run(client, "failed_upi")
    assert run["whatsapp_preview"]["template"] == "av_payment_link_v1"
    assert "Card ya OTP" in run["whatsapp_preview"]["body"]


def test_card_number_is_never_echoed(client):
    run = _run(client, "card_number")
    assert all("4111" not in t["text"] for t in run["transcript"])
    assert any(e["label"] == "card or OTP redacted" for e in run["events"])


def test_angry_refund_goes_to_a_human_and_opens_a_ticket(client):
    run = _run(client, "angry_refund")
    labels = [e["label"] for e in run["events"]]
    assert "warm_transfer" in labels and run["crm_ticket"] is not None


def test_kill_switch_stops_dials_in_under_five_seconds_and_releases(client):
    r = client.post("/demo/killswitch", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["engaged"] is True and r.json()["stopped_in_ms"] < 5000
    blocked = _run(client, "failed_upi")
    assert blocked["transcript"] == []
    assert any(e["label"] == "kill switch engaged" for e in blocked["events"])
    assert client.post("/demo/killswitch/release", headers=HEADERS).json()["engaged"] is False
    assert _run(client, "failed_upi")["transcript"]


def test_wrong_passcode_is_refused(client):
    r = client.post("/demo/run", json={"scenario": "failed_upi"}, headers={"x-demo-passcode": "x"})
    assert r.status_code == 401


def test_unknown_scenario_is_a_validation_error(client):
    r = client.post("/demo/run", json={"scenario": "refund_now"}, headers=HEADERS)
    assert r.status_code == 422


def test_demo_is_off_without_a_passcode(client, monkeypatch, session_factory, bus, settings, clock):
    monkeypatch.delenv("AV_DEMO_PASSCODE")
    rt = Runtime(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        providers=build_providers(settings),
        cipher=DataCipher(PostcallSettings().data_key),
        human_queue=InMemoryHumanQueue(),
    )
    off = TestClient(build_api(rt))
    r = off.post("/demo/run", json={"scenario": "failed_upi"}, headers=HEADERS)
    assert r.status_code == 404
