"""JSON-RPC 2.0 handler for the MCP methods we serve: initialize, tools/list, tools/call.

Transport-agnostic: an HTTP or stdio adapter passes each request and the caller's bearer
token. Only scoped API keys are accepted, every tools/call is audit-logged (including
refusals), and a tool's permission is checked against the key's effective permissions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.admin import apikeys
from app.admin.rbac import Principal, authorize
from app.core.audit import write_audit
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.db import transaction
from app.core.errors import AgodaVoiceError, AuthError, ForbiddenError, NotFoundError
from app.core.ids import new_trace_id
from app.mcp.tools import HUMAN_ONLY, TOOLS, McpContext

PROTOCOL_VERSION = "2025-06-18"
_CODES: dict[type[AgodaVoiceError], int] = {
    AuthError: -32001,
    ForbiddenError: -32003,
    NotFoundError: -32004,
}


@dataclass(frozen=True)
class McpServer:
    ctx: McpContext
    bus: EventBus
    clock: Clock
    tenant_id: str

    def handle(self, request: dict[str, Any], bearer: str) -> dict[str, Any]:
        rid = request.get("id")
        try:
            principal = self._principal(bearer)
            return {"jsonrpc": "2.0", "id": rid, "result": self._dispatch(request, principal)}
        except ValidationError as exc:
            return _error(rid, -32602, f"invalid arguments: {exc.error_count()} error(s)")
        except AgodaVoiceError as exc:
            return _error(rid, _CODES.get(type(exc), -32000), str(exc))

    def _principal(self, bearer: str) -> Principal:
        if not bearer.startswith(apikeys.PREFIX):
            raise AuthError("MCP accepts scoped API keys only")
        with transaction(self.ctx.session_factory) as s:
            return apikeys.authenticate(s, bearer, self.clock.now())

    def _dispatch(self, request: dict[str, Any], principal: Principal) -> dict[str, Any]:
        method = request.get("method")
        if method == "initialize":
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agoda-voice", "version": "0.1.0"},
            }
        if method == "tools/list":
            # A key sees only the tools its scopes allow.
            return {
                "tools": [
                    t.schema() for t in TOOLS.values() if t.permission in principal.permissions
                ]
            }
        if method == "tools/call":
            params = request.get("params") or {}
            return self._call(str(params.get("name", "")), params.get("arguments") or {}, principal)
        raise NotFoundError(f"method {method} is not served")

    def _call(self, name: str, arguments: dict[str, Any], principal: Principal) -> dict[str, Any]:
        tool = TOOLS.get(name)
        try:
            if name in HUMAN_ONLY:
                raise ForbiddenError(f"{name} is human-only; use the console")
            if tool is None:
                raise NotFoundError(f"no tool {name}")
            authorize(principal, tool.permission)
        except AgodaVoiceError as exc:
            self._audit(principal, name, f"refused: {exc.code}")
            raise
        args = tool.args.model_validate(arguments)
        result = tool.handler(self.ctx, principal, args)
        self._audit(principal, name, "ok")
        return {"content": [{"type": "text", "text": json.dumps(result)}], "isError": False}

    def _audit(self, principal: Principal, tool: str, outcome: str) -> None:
        with transaction(self.ctx.session_factory) as s:
            write_audit(
                s,
                self.bus,
                tenant_id=self.tenant_id,
                trace_id=new_trace_id(),
                at=self.clock.now(),
                actor=principal.actor,
                role=principal.role,
                action=f"mcp.{tool}",
                target="mcp",
                reason=outcome,
            )


def _error(rid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}
