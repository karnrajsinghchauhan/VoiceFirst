"""Contract tests for MetaCloudWhatsApp against recorded Graph API fixtures (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.core.errors import ConfigError, ProviderError
from app.providers.whatsapp.meta_cloud_api import MetaCloudWhatsApp, MetaWhatsAppSettings

FIX = Path(__file__).parents[1] / "fixtures/meta_whatsapp"
SEND = json.loads((FIX / "send_template.json").read_text())
SETTINGS = MetaWhatsAppSettings(
    access_token="EAAtest",
    phone_number_id="106540352242922",
    app_secret="appsecret",
    verify_token="verify",
)


def _client(handler):
    return MetaCloudWhatsApp(SETTINGS, transport=httpx.MockTransport(handler))


def test_send_template_matches_fixture():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SEND["response"])

    sent = _client(handler).send_template(
        "+919812345678",
        "av_payment_link_v1",
        "hinglish",
        {"first_name": "Priya", "link": "https://example.invalid/agoda/pay/abc"},
    )
    assert sent.provider_message_id == SEND["response"]["messages"][0]["id"]
    req = seen[0]
    assert req.url.path == "/v21.0/106540352242922/messages"
    assert req.headers["Authorization"] == "Bearer EAAtest"
    assert json.loads(req.content) == SEND["request"]


def test_send_text_in_window():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.t1"}]})

    assert _client(handler).send_text("+919812345678", "ok ji").provider_message_id == "wamid.t1"
    body = json.loads(seen[0].content)
    assert body["type"] == "text" and body["text"]["body"] == "ok ji"


@pytest.mark.parametrize(
    ("raw", "rating"), [("GREEN", "high"), ("YELLOW", "medium"), ("RED", "low")]
)
def test_quality_rating(raw: str, rating: str):
    client = _client(lambda r: httpx.Response(200, json={"quality_rating": raw, "id": "1"}))
    assert client.quality_rating() == rating


def test_unknown_quality_raises():
    with pytest.raises(ProviderError):
        _client(lambda r: httpx.Response(200, json={"quality_rating": "UNKNOWN"})).quality_rating()


@pytest.mark.parametrize("status", [400, 401, 429, 500])
def test_error_status_raises(status: int):
    with pytest.raises(ProviderError):
        _client(lambda r: httpx.Response(status, json={"error": {}})).send_text(
            "+919812345678", "x"
        )


def test_accepted_without_id_raises():
    with pytest.raises(ProviderError):
        _client(lambda r: httpx.Response(200, json={"messages": []})).send_text(
            "+919812345678", "x"
        )


def test_missing_keys_fail_at_construction():
    with pytest.raises(ConfigError):
        MetaCloudWhatsApp(MetaWhatsAppSettings(access_token="", phone_number_id=""))
