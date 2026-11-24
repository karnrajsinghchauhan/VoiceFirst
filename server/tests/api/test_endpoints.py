from app.core.audit import AuditRow
from app.core.ids import phone_hash
from app.handoff.transfer import InMemoryHumanQueue, warm_transfer
from app.postcall.store import TranscriptTurn, record_outcome, store_transcript
from tests.api.conftest import ADMIN, AUDITOR, OPS, RO
from tests.factories import PHONE
from tests.outcome_factory import make_outcome, make_summary


def _audit_actions(session_factory):
    with session_factory() as s:
        return [a.action for a in s.query(AuditRow).order_by(AuditRow.at)]


def test_healthz_needs_no_token(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_missing_and_unknown_token_are_401(client):
    assert client.get("/calls").status_code == 401
    r = client.get("/calls", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"] == "auth_error"


def test_read_only_cannot_engage_kill_switch(client):
    r = client.post("/killswitch", json={"engaged": True, "reason": "test"}, headers=RO)
    assert r.status_code == 403 and r.json()["error"] == "forbidden"


def test_kill_switch_engage_release_audited(client, session_factory):
    r = client.post("/killswitch", json={"engaged": True, "reason": "complaint spike"}, headers=OPS)
    assert r.status_code == 200
    body = r.json()
    assert body["engaged"] is True and body["actor"].startswith("ops:")
    assert body["reason"] == "complaint spike"
    assert client.get("/killswitch", headers=RO).json()["engaged"] is True
    client.post("/killswitch", json={"engaged": False, "reason": "all clear"}, headers=ADMIN)
    assert client.get("/killswitch", headers=RO).json()["engaged"] is False
    assert _audit_actions(session_factory) == ["kill_switch.engage", "kill_switch.release"]
    metrics = client.get("/metrics", headers=RO).text
    assert "av_kill_switch_engaged 0.0" in metrics
    assert 'av_http_requests_total{route="/killswitch",status="200"}' in metrics


def test_consent_record_lookup_opt_out(client, session_factory):
    r = client.post(
        "/consent",
        headers=ADMIN,
        json={
            "phone_e164": PHONE,
            "basis": "explicit",
            "purpose": "J1",
            "channel": "voice",
            "source_ref": "call_1",
        },
    )
    assert r.status_code == 200 and r.json()["expires_at"] is not None
    assert (
        client.post("/consent/lookup", json={"phone_e164": PHONE}, headers=OPS).status_code == 403
    )
    records = client.post("/consent/lookup", json={"phone_e164": PHONE}, headers=AUDITOR).json()
    assert len(records) == 1 and records[0]["revoked_at"] is None
    revoked = client.post(
        "/consent/opt-out", json={"phone_e164": PHONE, "channel": "whatsapp"}, headers=ADMIN
    ).json()
    assert revoked[0]["revoked_at"] is not None
    assert _audit_actions(session_factory) == [
        "consent.record",
        "consent.lookup",
        "consent.opt_out",
    ]


def test_consent_rejects_bad_phone(client):
    r = client.post(
        "/consent",
        headers=ADMIN,
        json={
            "phone_e164": "12345",
            "basis": "explicit",
            "purpose": "J1",
            "channel": "voice",
            "source_ref": "x",
        },
    )
    assert r.status_code == 422


def test_cli_upsert_and_list(client):
    body = {
        "series": "1600",
        "purpose": "transactional",
        "oap": "OAP",
        "a2p_declared": True,
        "declaration_ref": "DLT-1",
        "dlt_recorded_at": "2026-10-01T00:00:00Z",
        "status": "active",
    }
    assert client.put("/cli/+911600123456", json=body, headers=OPS).status_code == 403
    r = client.put("/cli/+911600123456", json=body, headers=ADMIN)
    assert r.status_code == 200 and r.json()["series"] == "1600"
    assert [c["cli_e164"] for c in client.get("/cli", headers=RO).json()] == ["+911600123456"]


def test_calls_and_transcript(client, deps, session_factory, settings, clock):
    outcome = make_outcome(clock.now())
    with session_factory() as s:
        ph = phone_hash(PHONE, settings.phone_pepper)
        record_outcome(s, deps.bus, outcome, ph)
        store_transcript(
            s,
            deps.cipher,
            tenant_id="agoda-in",
            call_id=outcome.call_id,
            phone_hash=ph,
            at=clock.now(),
            turns=[TranscriptTurn("customer", "OTP 1 2 3 4 5 6")],
        )
        s.commit()
    assert client.get("/calls", headers=RO).json()[0]["call_id"] == outcome.call_id
    assert client.get(f"/calls/{outcome.call_id}", headers=RO).json()["outcome"] == "link_sent"
    assert client.get("/calls/call_nope", headers=RO).status_code == 404
    assert client.get(f"/calls/{outcome.call_id}/transcript", headers=RO).status_code == 403
    lines = client.get(f"/calls/{outcome.call_id}/transcript", headers=AUDITOR).json()
    assert lines == [{"speaker": "customer", "text": "OTP [REDACTED_OTP]"}]
    assert "transcript.read" in _audit_actions(session_factory)


def test_handoff_list_and_ack(client, deps, session_factory, clock):
    summary = make_summary(clock.now())
    with session_factory() as s:
        warm_transfer(s, deps.bus, InMemoryHumanQueue(), clock, summary, "female")
        s.commit()
    listed = client.get("/handoff", headers=RO).json()
    assert listed[0]["result"] == "callback_scheduled"
    assert client.get(f"/handoff/{summary.call_id}", headers=RO).json()["reason"] == "dispute"
    r = client.post(f"/handoff/{summary.call_id}", json={"action": "acknowledge"}, headers=OPS)
    assert r.status_code == 200
    again = client.post(f"/handoff/{summary.call_id}", json={"action": "acknowledge"}, headers=OPS)
    assert again.status_code == 409


def test_rights_request_flow(client):
    opened = client.post(
        "/rights-requests", json={"phone_e164": PHONE, "kind": "erasure"}, headers=ADMIN
    ).json()
    assert opened["status"] == "open"
    assert (
        client.get("/rights-requests", headers=AUDITOR).json()[0]["request_id"]
        == opened["request_id"]
    )
    assert (
        client.post(
            f"/rights-requests/{opened['request_id']}/acknowledge", headers=AUDITOR
        ).status_code
        == 403
    )
    done = client.post(
        f"/rights-requests/{opened['request_id']}/complete",
        json={"phone_e164": PHONE},
        headers=ADMIN,
    ).json()
    assert done["request"]["status"] == "completed" and done["export"] is None


def test_campaign_pause_audited(client, session_factory):
    assert client.get("/campaigns", headers=RO).json()[0]["status"] == "active"
    r = client.post("/campaigns/cmp_j1/pause", json={"reason": "quality review"}, headers=OPS)
    assert r.json()["status"] == "paused"
    assert (
        client.post("/campaigns/nope/pause", json={"reason": "x y z"}, headers=OPS).status_code
        == 404
    )
    assert _audit_actions(session_factory) == ["campaign.pause"]


def test_simulate_and_incidents(client):
    r = client.post("/simulate", json={"persona": "C-01", "seed": 1, "purpose": "J1"}, headers=OPS)
    assert r.status_code == 200 and r.json()["persona"] == "C-01"
    assert (
        client.post(
            "/simulate", json={"persona": "C-01", "seed": 1, "purpose": "J1"}, headers=RO
        ).status_code
        == 403
    )
    inc = client.post(
        "/incidents",
        headers=OPS,
        json={
            "kind": "security",
            "summary": "token leaked",
            "detected_at": "2026-11-23T06:00:00Z",
        },
    ).json()
    assert inc["cert_in_due_at"] == "2026-11-23T12:00:00Z"
    assert len(client.get("/incidents", headers=AUDITOR).json()) == 1


def test_audit_endpoint(client):
    client.post("/killswitch", json={"engaged": True, "reason": "drill"}, headers=OPS)
    assert client.get("/audit", headers=RO).status_code == 403
    events = client.get("/audit", headers=AUDITOR).json()
    assert events[0]["action"] == "kill_switch.engage" and events[0]["reason"] == "drill"


def test_openapi_carries_disclaimer(client):
    assert (
        "not affiliated with or endorsed by Agoda"
        in client.get("/openapi.json").json()["info"]["description"]
    )
