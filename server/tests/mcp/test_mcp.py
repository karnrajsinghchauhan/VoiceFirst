"""MCP scaffold: scoped keys only, scopes decide the tools, human-only actions are refused,
and every tools/call is audit-logged."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.admin import apikeys
from app.campaigns.service import CampaignPort
from app.core.audit import AuditRow
from app.core.db import transaction
from app.mcp.server import McpServer
from app.mcp.tools import HUMAN_ONLY, HUMAN_ONLY_PERMISSIONS, TOOLS, McpContext


@pytest.fixture
def server(session_factory, bus, settings, clock, tmp_path) -> McpServer:
    ctx = McpContext(
        session_factory=session_factory,
        campaigns=CampaignPort(session_factory, settings.tenant_id, clock),
        reports_dir=tmp_path,
    )
    return McpServer(ctx=ctx, bus=bus, clock=clock, tenant_id=settings.tenant_id)


def _key(session_factory, settings, clock, role: str, scopes=None) -> str:
    with transaction(session_factory) as s:
        return apikeys.issue(
            s,
            tenant_id=settings.tenant_id,
            name=f"agent-{role}",
            role=role,
            scopes=scopes,
            created_by="admin",
            now=clock.now(),
            ttl=None,
        ).token


def _call(server: McpServer, token: str, name: str, arguments: dict | None = None) -> dict:
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }
    return server.handle(req, token)


def _audit(session_factory) -> list[tuple[str, str]]:
    with transaction(session_factory) as s:
        return [(r.action, r.reason) for r in s.scalars(select(AuditRow).order_by(AuditRow.at))]


def test_no_tool_touches_human_only_ground():
    assert not set(TOOLS) & HUMAN_ONLY
    assert all(t.permission not in HUMAN_ONLY_PERMISSIONS for t in TOOLS.values())


def test_only_scoped_api_keys_are_accepted(server):
    out = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, "dev-ops-token")
    assert out["error"]["code"] == -32001


def test_initialize_and_scoped_tool_list(server, session_factory, settings, clock):
    token = _key(
        session_factory, settings, clock, "ops", frozenset({"campaigns:read", "calls:read"})
    )
    init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, token)
    assert init["result"]["capabilities"] == {"tools": {}}
    tools = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, token)["result"][
        "tools"
    ]
    assert {t["name"] for t in tools} == {
        "list_campaigns",
        "list_call_outcomes",
        "get_call_outcome",
    }


def test_an_agent_can_pause_and_start_a_campaign_and_it_is_audited(
    server, session_factory, settings, clock
):
    token = _key(session_factory, settings, clock, "ops")
    paused = _call(
        server,
        token,
        "pause_campaign",
        {"campaign_id": "cmp_j1", "reason": "agent: complaint spike"},
    )
    assert json.loads(paused["result"]["content"][0]["text"])["status"] == "paused"
    started = _call(
        server, token, "start_campaign", {"campaign_id": "cmp_j1", "reason": "agent: resolved"}
    )
    assert json.loads(started["result"]["content"][0]["text"])["status"] == "active"
    assert ("mcp.pause_campaign", "ok") in _audit(session_factory)
    assert ("mcp.start_campaign", "ok") in _audit(session_factory)


def test_scopes_are_enforced_and_refusals_are_audited(server, session_factory, settings, clock):
    token = _key(session_factory, settings, clock, "ops", frozenset({"campaigns:read"}))
    out = _call(server, token, "pause_campaign", {"campaign_id": "cmp_j1", "reason": "try"})
    assert out["error"]["code"] == -32003
    assert any(
        a == "mcp.pause_campaign" and r.startswith("refused") for a, r in _audit(session_factory)
    )


@pytest.mark.parametrize("name", sorted(HUMAN_ONLY))
def test_human_only_actions_are_refused_even_for_admin(
    server, session_factory, settings, clock, name
):
    token = _key(session_factory, settings, clock, "admin")
    out = _call(server, token, name)
    assert out["error"]["code"] == -32003
    assert "human-only" in out["error"]["message"]


def test_bad_arguments_are_a_validation_error(server, session_factory, settings, clock):
    token = _key(session_factory, settings, clock, "ops")
    out = _call(server, token, "list_call_outcomes", {"limit": 10_000})
    assert out["error"]["code"] == -32602


def test_qa_report_reads_the_latest_scorecard(
    server, session_factory, settings, clock, tmp_path: Path
):
    token = _key(session_factory, settings, clock, "ops")
    assert _call(server, token, "get_qa_report")["error"]["code"] == -32004
    run = tmp_path / "20261127T000000Z-text"
    run.mkdir()
    (run / "results.json").write_text(
        json.dumps({"scorecard": {"guardrail_rate": 1.0}, "records": []})
    )
    body = json.loads(_call(server, token, "get_qa_report")["result"]["content"][0]["text"])
    assert body == {"report": run.name, "scorecard": {"guardrail_rate": 1.0}}
