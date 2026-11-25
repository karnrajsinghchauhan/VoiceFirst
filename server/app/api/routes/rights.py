"""DPDP rights request endpoints (REQ-DPDP-05)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.admin.rbac import Principal
from app.api.deps import Db, Deps, require
from app.rights import workflow
from app.rights.models import RightsRequestRow

router = APIRouter()

_E164 = r"^\+[1-9][0-9]{6,14}$"


class _In(BaseModel):
    # Strict: a request that violates the documented schema is refused, never coerced.
    model_config = ConfigDict(extra="forbid")


class RightsRequestView(BaseModel):
    request_id: str
    kind: Literal["access", "correction", "erasure"]
    status: Literal["open", "acknowledged", "completed"]
    received_at: datetime
    ack_due_at: datetime
    due_at: datetime
    acknowledged_at: datetime | None
    completed_at: datetime | None
    result: dict[str, Any]


def _view(row: RightsRequestRow) -> RightsRequestView:
    return RightsRequestView(
        request_id=row.request_id,
        kind=row.kind,
        status=row.status,
        received_at=row.received_at,
        ack_due_at=row.ack_due_at,
        due_at=row.due_at,
        acknowledged_at=row.acknowledged_at,
        completed_at=row.completed_at,
        result=row.result,
    )


def _actor(principal: Principal) -> workflow.Actor:
    return workflow.Actor(actor=principal.actor, role=principal.role)


class RightsRequestIn(_In):
    phone_e164: str = Field(pattern=_E164)
    kind: Literal["access", "correction", "erasure"]


@router.post("/rights-requests", tags=["rights"])
def open_request(
    body: RightsRequestIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("rights:write"))],
) -> RightsRequestView:
    row = workflow.open_request(
        db,
        deps.bus,
        deps.settings,
        deps.rights_sla,
        phone_e164=body.phone_e164,
        kind=body.kind,
        at=deps.clock.now(),
        actor=_actor(principal),
    )
    return _view(row)


@router.get("/rights-requests", tags=["rights"])
def list_requests(
    db: Db,
    _p: Annotated[Principal, Depends(require("rights:read"))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[RightsRequestView]:
    return [_view(r) for r in workflow.list_requests(db, limit)]


@router.post("/rights-requests/{request_id}/acknowledge", tags=["rights"])
def acknowledge(
    request_id: str,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("rights:write"))],
) -> RightsRequestView:
    row = workflow.acknowledge(
        db,
        deps.bus,
        deps.settings,
        request_id=request_id,
        at=deps.clock.now(),
        actor=_actor(principal),
    )
    return _view(row)


class CompleteIn(_In):
    phone_e164: str = Field(pattern=_E164)
    note: str = Field(default="", max_length=2000)


class CompleteOut(BaseModel):
    request: RightsRequestView
    export: dict[str, Any] | None


@router.post("/rights-requests/{request_id}/complete", tags=["rights"])
def complete(
    request_id: str,
    body: CompleteIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("rights:write"))],
) -> CompleteOut:
    actor = _actor(principal)
    now = deps.clock.now()
    kind = workflow.get_request(db, request_id).kind
    export: dict[str, Any] | None = None
    if kind == "access":
        export = workflow.fulfil_access(
            db,
            deps.bus,
            deps.settings,
            deps.cipher,
            request_id=request_id,
            phone_e164=body.phone_e164,
            at=now,
            actor=actor,
        )
    elif kind == "correction":
        workflow.fulfil_correction(
            db,
            deps.bus,
            deps.settings,
            request_id=request_id,
            phone_e164=body.phone_e164,
            at=now,
            actor=actor,
            note=body.note,
        )
    else:
        workflow.fulfil_erasure(
            db,
            deps.bus,
            deps.settings,
            request_id=request_id,
            phone_e164=body.phone_e164,
            at=now,
            actor=actor,
        )
    return CompleteOut(request=_view(workflow.get_request(db, request_id)), export=export)
