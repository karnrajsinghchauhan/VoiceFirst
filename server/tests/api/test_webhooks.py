"""Inbound webhooks: signature verification, replay protection, and what they act on (S8)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import timedelta
from pathlib import Path

from google.protobuf.json_format import MessageToJson
from livekit import api as lk

from app.api.stubs import STUB_WEBHOOK_SECRETS as SECRETS
from app.compliance.models import OptOutRow
from app.core.ids import phone_hash

FIX = Path(__file__).parents[1] / "fixtures/meta_whatsapp"


def _meta_body(name: str, ts: int) -> bytes:
    payload = json.loads((FIX / name).read_text())
    for change in payload["entry"][0]["changes"]:
        for item in change["value"].get("messages", []) + change["value"].get("statuses", []):
            item["timestamp"] = str(ts)
    return json.dumps(payload).encode()


def _sign(body: bytes, secret: str = SECRETS.meta_app_secret) -> dict[str, str]:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}


def test_handshake_echoes_challenge_only_with_the_right_token(client):
    ok = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": SECRETS.meta_verify_token,
            "hub.challenge": "1158201444",
        },
    )
    assert ok.status_code == 200 and ok.text == "1158201444"
    bad = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "x"},
    )
    assert bad.status_code == 401


def test_signed_stop_reply_withdraws_consent(client, clock, session_factory, settings):
    body = _meta_body("inbound_message.json", int(clock.now().timestamp()))
    r = client.post("/webhooks/whatsapp", content=body, headers=_sign(body))
    assert r.status_code == 200, r.text
    assert r.json()["actions"] == ["withdrawn"]
    with session_factory() as s:
        assert s.get(OptOutRow, phone_hash("+919812345678", settings.phone_pepper)) is not None


def test_bad_signature_is_refused_and_acts_on_nothing(client, clock, session_factory, settings):
    body = _meta_body("inbound_message.json", int(clock.now().timestamp()))
    r = client.post("/webhooks/whatsapp", content=body, headers=_sign(body, "wrong-secret"))
    assert r.status_code == 401
    missing = client.post(
        "/webhooks/whatsapp", content=body, headers={"Content-Type": "application/json"}
    )
    assert missing.status_code == 401
    with session_factory() as s:
        assert s.get(OptOutRow, phone_hash("+919812345678", settings.phone_pepper)) is None


def test_tampered_body_is_refused(client, clock):
    body = _meta_body("inbound_message.json", int(clock.now().timestamp()))
    headers = _sign(body)
    r = client.post("/webhooks/whatsapp", content=body.replace(b"STOP", b"haan"), headers=headers)
    assert r.status_code == 401


def test_replayed_delivery_is_rejected(client, clock):
    body = _meta_body("inbound_message.json", int(clock.now().timestamp()))
    assert client.post("/webhooks/whatsapp", content=body, headers=_sign(body)).status_code == 200
    again = client.post("/webhooks/whatsapp", content=body, headers=_sign(body))
    assert again.status_code == 409 and again.json()["error"] == "webhook_replay"


def test_stale_delivery_is_rejected(client, clock):
    stale = int((clock.now() - timedelta(minutes=11)).timestamp())
    body = _meta_body("inbound_message.json", stale)
    r = client.post("/webhooks/whatsapp", content=body, headers=_sign(body))
    assert r.status_code == 409


def test_status_callbacks_are_recorded(client, clock, session_factory):
    from app.webhooks_in.models import WebhookReceiptRow

    body = _meta_body("status_update.json", int(clock.now().timestamp()))
    r = client.post("/webhooks/whatsapp", content=body, headers=_sign(body))
    assert r.json()["actions"] == ["status"]
    with session_factory() as s:
        row = s.query(WebhookReceiptRow).one()
        assert (row.kind, row.detail) == ("status", "delivered")


def _livekit_event(clock, event_id: str = "EV_1") -> bytes:
    ev = lk.WebhookEvent(
        event="room_finished", id=event_id, created_at=int(clock.now().timestamp())
    )
    ev.room.name = "call_abc"
    return MessageToJson(ev).encode()


def _livekit_auth(body: bytes, secret: str = SECRETS.livekit_api_secret) -> dict[str, str]:
    digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
    token = lk.AccessToken(SECRETS.livekit_api_key, secret).with_sha256(digest).to_jwt()
    return {"Authorization": token, "Content-Type": "application/webhook+json"}


def test_signed_telephony_webhook_is_accepted_once(client, clock):
    body = _livekit_event(clock)
    r = client.post("/webhooks/telephony", content=body, headers=_livekit_auth(body))
    assert r.status_code == 200 and r.json() == {"event": "room_finished"}
    again = client.post("/webhooks/telephony", content=body, headers=_livekit_auth(body))
    assert again.status_code == 409


def test_telephony_webhook_with_wrong_secret_or_body_is_refused(client, clock):
    body = _livekit_event(clock, "EV_2")
    bad_secret = _livekit_auth(body, "x" * 36)
    assert client.post("/webhooks/telephony", content=body, headers=bad_secret).status_code == 401
    other = _livekit_event(clock, "EV_3")
    swapped = client.post("/webhooks/telephony", content=other, headers=_livekit_auth(body))
    assert swapped.status_code == 401
