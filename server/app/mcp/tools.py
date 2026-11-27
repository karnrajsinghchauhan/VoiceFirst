"""The tools a client's agents may call over MCP, each bound to one RBAC permission.

The kill switch, consent and anything that moves money are deliberately absent: those stay
with a person in the console (docs/mcp.md). HUMAN_ONLY names them so a request gets a clear
refusal instead of "unknown tool".
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from app.admin.rbac import Permission, Principal
from app.api.ports import CampaignService
from app.core.db import transaction
from app.core.errors import NotFoundError
from app.postcall import store

HUMAN_ONLY = frozenset(
    {
        "engage_kill_switch",
        "release_kill_switch",
        "record_consent",
        "revoke_consent",
        "mark_dnc",
        "send_payment_link",
        "refund",
        "cancel_booking",
        "issue_credit",
    }
)
# Permissions no MCP tool may require: changing them is a human decision in the console.
HUMAN_ONLY_PERMISSIONS: frozenset[Permission] = frozenset(
    {"killswitch:write", "consent:write", "apikeys:write"}
)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArgs(_In):
    pass


class CampaignArgs(_In):
    campaign_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=500)


class ListCallsArgs(_In):
    limit: int = Field(default=20, ge=1, le=100)


class CallArgs(_In):
    call_id: str = Field(min_length=1, max_length=64)


@dataclass(frozen=True)
class McpContext:
    session_factory: sessionmaker[Session]
    campaigns: CampaignService
    reports_dir: Path


Handler = Callable[[McpContext, Principal, Any], Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    permission: Permission
    args: type[_In]
    handler: Handler
    mutates: bool

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.args.model_json_schema(),
        }


def _list_campaigns(ctx: McpContext, _p: Principal, _a: NoArgs) -> Any:
    return [c.model_dump(mode="json") for c in ctx.campaigns.list_campaigns()]


def _pause(ctx: McpContext, p: Principal, a: CampaignArgs) -> Any:
    return ctx.campaigns.pause(a.campaign_id, p.actor, a.reason).model_dump(mode="json")


def _start(ctx: McpContext, p: Principal, a: CampaignArgs) -> Any:
    # Starting resumes a paused campaign; every call it makes still passes every gate.
    return ctx.campaigns.resume(a.campaign_id, p.actor, a.reason).model_dump(mode="json")


def _list_calls(ctx: McpContext, _p: Principal, a: ListCallsArgs) -> Any:
    with transaction(ctx.session_factory) as s:
        return [o.model_dump(mode="json") for o in store.list_outcomes(s, a.limit)]


def _get_call(ctx: McpContext, _p: Principal, a: CallArgs) -> Any:
    with transaction(ctx.session_factory) as s:
        return store.get_outcome(s, a.call_id).model_dump(mode="json")


def _qa_report(ctx: McpContext, _p: Principal, _a: NoArgs) -> Any:
    """The newest eval scorecard written by `make eval` (reports/<ts>-text/results.json)."""
    runs = sorted(p for p in ctx.reports_dir.glob("*-text/results.json") if p.is_file())
    if not runs:
        raise NotFoundError("no QA report yet: run make eval")
    scorecard = json.loads(runs[-1].read_text())["scorecard"]
    return {"report": runs[-1].parent.name, "scorecard": scorecard}


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        Tool(
            "list_campaigns",
            "List campaigns and whether each is paused.",
            "campaigns:read",
            NoArgs,
            _list_campaigns,
            False,
        ),
        Tool(
            "pause_campaign",
            "Pause a campaign; queued calls wait.",
            "campaigns:write",
            CampaignArgs,
            _pause,
            True,
        ),
        Tool(
            "start_campaign",
            "Resume a paused campaign; every call still passes every gate.",
            "campaigns:write",
            CampaignArgs,
            _start,
            True,
        ),
        Tool(
            "list_call_outcomes",
            "Recent call outcomes (redacted; no transcripts).",
            "calls:read",
            ListCallsArgs,
            _list_calls,
            False,
        ),
        Tool(
            "get_call_outcome",
            "One call outcome by id (redacted).",
            "calls:read",
            CallArgs,
            _get_call,
            False,
        ),
        Tool(
            "get_qa_report",
            "The latest QA scorecard from the eval suite.",
            "metrics:read",
            NoArgs,
            _qa_report,
            False,
        ),
    )
}
