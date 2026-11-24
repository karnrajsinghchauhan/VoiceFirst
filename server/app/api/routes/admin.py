"""Enterprise administration: API keys (issue, list, rotate, revoke) and audit export."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.admin import apikeys
from app.admin.rbac import Permission, Principal
from app.api.deps import Db, Deps, require
from app.api.types import DaysTtl
from app.core.audit import AuditRow, write_audit
from app.core.ids import new_trace_id

router = APIRouter()


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApiKeyIn(_In):
    name: str = Field(min_length=3, max_length=80)
    role: Literal["admin", "ops", "auditor", "read_only"]
    scopes: list[Permission] | None = None
    expires_in_days: DaysTtl | None = None
    reason: str = Field(min_length=3, max_length=500)


class ReasonIn(_In):
    reason: str = Field(min_length=3, max_length=500)


class IssuedKeyOut(BaseModel):
    key_id: str
    token: str = Field(description="Shown once. Store it in your secret manager.")


class ApiKeyOut(BaseModel):
    key_id: str
    name: str
    role: str
    scopes: list[str] | None
    created_at: datetime
    created_by: str
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    replaced_by: str | None


def _audit(deps: Deps, db: Db, p: Principal, action: str, target: str, reason: str) -> None:
    write_audit(
        db,
        deps.bus,
        tenant_id=deps.settings.tenant_id,
        trace_id=new_trace_id(),
        at=deps.clock.now(),
        actor=p.actor,
        role=p.role,
        action=action,
        target=target,
        reason=reason,
    )


def _out(row: apikeys.ApiKeyRow) -> ApiKeyOut:
    return ApiKeyOut(
        key_id=row.key_id,
        name=row.name,
        role=row.role,
        scopes=row.scopes,
        created_at=row.created_at,
        created_by=row.created_by,
        expires_at=row.expires_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
        replaced_by=row.replaced_by,
    )


@router.post("/api-keys", tags=["api-keys"])
def issue_key(
    body: ApiKeyIn, deps: Deps, db: Db, p: Annotated[Principal, Depends(require("apikeys:write"))]
) -> IssuedKeyOut:
    issued = apikeys.issue(
        db,
        tenant_id=deps.settings.tenant_id,
        name=body.name,
        role=body.role,
        scopes=frozenset(body.scopes) if body.scopes is not None else None,
        created_by=p.actor,
        now=deps.clock.now(),
        ttl=timedelta(days=body.expires_in_days) if body.expires_in_days else None,
    )
    _audit(deps, db, p, "api_key.issue", f"api_key:{issued.key_id}", body.reason)
    return IssuedKeyOut(key_id=issued.key_id, token=issued.token)


@router.get("/api-keys", tags=["api-keys"])
def list_keys(
    deps: Deps, db: Db, _p: Annotated[Principal, Depends(require("apikeys:write"))]
) -> list[ApiKeyOut]:
    return [_out(r) for r in apikeys.list_keys(db, deps.settings.tenant_id)]


@router.post("/api-keys/{key_id}/rotate", tags=["api-keys"])
def rotate_key(
    key_id: str,
    body: ReasonIn,
    deps: Deps,
    db: Db,
    p: Annotated[Principal, Depends(require("apikeys:write"))],
) -> IssuedKeyOut:
    issued = apikeys.rotate(db, key_id, created_by=p.actor, now=deps.clock.now())
    _audit(deps, db, p, "api_key.rotate", f"api_key:{key_id}->{issued.key_id}", body.reason)
    return IssuedKeyOut(key_id=issued.key_id, token=issued.token)


@router.post("/api-keys/{key_id}/revoke", tags=["api-keys"])
def revoke_key(
    key_id: str,
    body: ReasonIn,
    deps: Deps,
    db: Db,
    p: Annotated[Principal, Depends(require("apikeys:write"))],
) -> ApiKeyOut:
    apikeys.revoke(db, key_id, deps.clock.now())
    _audit(deps, db, p, "api_key.revoke", f"api_key:{key_id}", body.reason)
    return _out(db.get_one(apikeys.ApiKeyRow, key_id))


_AUDIT_FIELDS = ("audit_id", "at", "actor", "role", "action", "target", "reason", "trace_id")


@router.get(
    "/audit/export",
    tags=["audit"],
    responses={200: {"content": {"text/csv": {}, "application/json": {}}}},
)
def export_audit(
    deps: Deps,
    db: Db,
    p: Annotated[Principal, Depends(require("audit:read"))],
    fmt: Annotated[Literal["csv", "json"], Query(alias="format")] = "csv",
) -> Response:
    """Every privileged action, oldest first. The export itself is audit-logged."""
    rows = db.scalars(select(AuditRow).order_by(AuditRow.at, AuditRow.audit_id)).all()
    records = [
        {f: (getattr(r, f).isoformat() if f == "at" else getattr(r, f)) for f in _AUDIT_FIELDS}
        for r in rows
    ]
    _audit(deps, db, p, "audit.export", f"audit:{fmt}", f"{len(records)} rows")
    if fmt == "json":
        return Response(json.dumps(records, ensure_ascii=False), media_type="application/json")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_AUDIT_FIELDS)
    writer.writeheader()
    writer.writerows(records)
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit.csv"},
    )
