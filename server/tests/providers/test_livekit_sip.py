"""Contract tests for LiveKitSipTelephony against recorded Twirp fixtures (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import jwt
import pytest

from app.core.errors import ConfigError, ProviderError
from app.providers.livekit_settings import LiveKitSettings
from app.providers.telephony.livekit_sip import (
    CREATE_PATH,
    DELETE_ROOM_PATH,
    LiveKitSipTelephony,
    SipTrunkSettings,
)

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures/livekit_sip/create_sip_participant.json").read_text()
)
LK = LiveKitSettings(url="wss://lk.example.invalid", api_key="APIkey", api_secret="s" * 32)
TRUNK = SipTrunkSettings(outbound_trunk_id="ST_test123")


def _client(handler):
    return LiveKitSipTelephony("plivo", LK, TRUNK, transport=httpx.MockTransport(handler))


def test_place_call_sends_the_documented_request_and_reads_the_room():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=FIXTURE["response"])

    placed = _client(handler).place_call("+919812345678", "+911600123456", "call_abc")
    assert placed.provider_call_id == "call_abc"
    req = seen[0]
    assert req.url.path == CREATE_PATH and req.url.host == "lk.example.invalid"
    assert json.loads(req.content) == FIXTURE["request"]
    claims = jwt.decode(
        req.headers["Authorization"].removeprefix("Bearer "), "s" * 32, algorithms=["HS256"]
    )
    assert claims["sip"]["call"] is True and claims["video"]["room"] == "call_abc"


def test_hang_up_deletes_the_room():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    _client(handler).hang_up("call_abc")
    assert seen[0].url.path == DELETE_ROOM_PATH
    assert json.loads(seen[0].content) == {"room": "call_abc"}


@pytest.mark.parametrize("status", [400, 401, 500, 503])
def test_error_status_raises(status: int):
    client = _client(lambda r: httpx.Response(status, json={"code": "x", "msg": "y"}))
    with pytest.raises(ProviderError):
        client.place_call("+919812345678", "+911600123456", "call_abc")


def test_unexpected_body_raises():
    client = _client(lambda r: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(ProviderError):
        client.place_call("+919812345678", "+911600123456", "call_abc")


def test_missing_keys_fail_at_construction():
    with pytest.raises(ConfigError):
        LiveKitSipTelephony("plivo", LiveKitSettings(url="", api_key="", api_secret=""), TRUNK)
    with pytest.raises(ConfigError):
        LiveKitSipTelephony("exotel", LK, SipTrunkSettings(outbound_trunk_id=""))
