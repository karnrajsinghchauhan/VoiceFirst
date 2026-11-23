import base64
import json

import httpx
import pytest

from app.core.errors import (
    ConfigError,
    ProviderError,
    ProviderNotBuiltError,
    ProviderTimeoutError,
)
from app.crm.cases import open_case, priority_for
from app.crm.factory import make_crm
from app.providers.crm.mock import MockCrm
from app.providers.crm.zendesk import ZendeskCrm, ZendeskSettings
from tests.factories import make_settings
from tests.outcome_factory import make_summary

ZS = ZendeskSettings(subdomain="acme", email="bot@example.invalid", api_token="tok")  # noqa: S106


def _crm(handler):
    return ZendeskCrm(ZS, transport=httpx.MockTransport(handler))


def test_create_ticket_payload_and_auth(clock):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(201, json={"ticket": {"id": 42, "status": "new"}})

    summary = make_summary(clock.now())
    ticket = open_case(_crm(handler), summary, "grievance")
    assert ticket.ticket_id == "42"
    assert ticket.url == "https://acme.zendesk.com/agent/tickets/42"
    req = seen[0]
    assert req.method == "POST" and req.url.path == "/api/v2/tickets.json"
    expected = base64.b64encode(b"bot@example.invalid/token:tok").decode()
    assert req.headers["authorization"] == f"Basic {expected}"
    body = json.loads(req.content)["ticket"]
    assert body["comment"]["public"] is False
    assert body["external_id"] == summary.call_id
    assert body["priority"] == "urgent"
    assert "agoda_voice" in body["tags"]
    assert "+91" not in req.content.decode() and "BK00001234" not in req.content.decode()


def test_add_note_is_internal():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ticket": {"id": 7}})

    _crm(handler).add_note("7", "summary")
    assert seen[0].method == "PUT" and seen[0].url.path == "/api/v2/tickets/7.json"
    assert json.loads(seen[0].content)["ticket"]["comment"] == {"body": "summary", "public": False}


def test_http_error_is_provider_error():
    crm = _crm(lambda r: httpx.Response(500))
    with pytest.raises(ProviderError):
        crm.add_note("1", "x")


def test_timeout_is_typed():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ProviderTimeoutError):
        _crm(handler).add_note("1", "x")


def test_unexpected_body_is_provider_error():
    crm = _crm(lambda r: httpx.Response(201, json={"nope": 1}))
    with pytest.raises(ProviderError):
        crm.create_ticket("s", "b", "ref", [], "normal")


def test_bad_priority_rejected_before_network():
    crm = _crm(lambda r: pytest.fail("network called"))
    with pytest.raises(ProviderError):
        crm.create_ticket("s", "b", "ref", [], "critical")


def test_incomplete_settings_fail_at_construction():
    with pytest.raises(ConfigError):
        ZendeskCrm(ZendeskSettings())


def test_factory_builds_one_provider_by_name():
    assert isinstance(make_crm(make_settings()), MockCrm)
    with pytest.raises(ProviderNotBuiltError):
        make_crm(make_settings(crm="salesforce"))
    with pytest.raises(ProviderNotBuiltError):
        make_crm(make_settings(crm="hubspot"))


def test_priority_mapping(clock):
    assert priority_for(make_summary(clock.now(), reason="dispute")) == "urgent"
    assert (
        priority_for(make_summary(clock.now(), reason="asked_for_human", sentiment="angry"))
        == "high"
    )
    assert (
        priority_for(make_summary(clock.now(), reason="asked_for_human", sentiment="calm"))
        == "normal"
    )
