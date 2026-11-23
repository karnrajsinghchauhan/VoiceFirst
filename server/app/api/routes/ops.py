"""Operational endpoints: health, metrics, kill switch, campaigns, simulate, incidents, audit."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.admin.rbac import Principal
from app.api.deps import Db, Deps, require
from app.api.ports import CampaignView, IncidentKind, IncidentView, SimulationResult
from app.compliance import killswitch
from app.compliance.models import KillSwitchRow
from app.contracts.generated.audit_event import AuditEvent
from app.core.audit import AuditRow, write_audit
from app.core.ids import new_trace_id
from app.core.types import Language, Purpose

router = APIRouter()


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Health(BaseModel):
    status: Literal["ok"]


@router.get("/healthz", tags=["ops"])
def healthz() -> Health:
    return Health(status="ok")


@router.get("/metrics", tags=["ops"], response_class=PlainTextResponse)
def metrics(
    deps: Deps, _p: Annotated[Principal, Depends(require("metrics:read"))]
) -> PlainTextResponse:
    return PlainTextResponse(generate_latest(deps.metrics.registry).decode())


class KillSwitchIn(_In):
    engaged: bool
    reason: str = Field(min_length=3, max_length=500)


class KillSwitchState(BaseModel):
    engaged: bool
    actor: str | None
    reason: str | None
    changed_at: datetime | None


def _kill_state(row: KillSwitchRow | None) -> KillSwitchState:
    if row is None:
        return KillSwitchState(engaged=False, actor=None, reason=None, changed_at=None)
    return KillSwitchState(
        engaged=row.engaged, actor=row.actor, reason=row.reason, changed_at=row.changed_at
    )


@router.get("/killswitch", tags=["killswitch"])
def get_killswitch(
    deps: Deps, db: Db, _p: Annotated[Principal, Depends(require("killswitch:read"))]
) -> KillSwitchState:
    return _kill_state(db.get(KillSwitchRow, deps.settings.tenant_id))


@router.post("/killswitch", tags=["killswitch"])
def set_killswitch(
    body: KillSwitchIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("killswitch:write"))],
) -> KillSwitchState:
    action = killswitch.engage if body.engaged else killswitch.release
    action(
        db,
        deps.bus,
        deps.clock,
        tenant_id=deps.settings.tenant_id,
        actor=principal.actor,
        role=principal.role,
        reason=body.reason,
    )
    deps.metrics.kill_switch.set(1 if body.engaged else 0)
    return _kill_state(db.get(KillSwitchRow, deps.settings.tenant_id))


@router.get("/campaigns", tags=["campaigns"])
def list_campaigns(
    deps: Deps, _p: Annotated[Principal, Depends(require("campaigns:read"))]
) -> list[CampaignView]:
    return deps.campaigns.list_campaigns()


class ReasonIn(_In):
    reason: str = Field(min_length=3, max_length=500)


def _audit(deps: Deps, db: Db, principal: Principal, action: str, target: str, reason: str) -> None:
    write_audit(
        db,
        deps.bus,
        tenant_id=deps.settings.tenant_id,
        trace_id=new_trace_id(),
        at=deps.clock.now(),
        actor=principal.actor,
        role=principal.role,
        action=action,
        target=target,
        reason=reason,
    )


@router.post("/campaigns/{campaign_id}/pause", tags=["campaigns"])
def pause_campaign(
    campaign_id: str,
    body: ReasonIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("campaigns:write"))],
) -> CampaignView:
    view = deps.campaigns.pause(campaign_id, principal.actor, body.reason)
    _audit(deps, db, principal, "campaign.pause", f"campaign:{campaign_id}", body.reason)
    return view


@router.post("/campaigns/{campaign_id}/resume", tags=["campaigns"])
def resume_campaign(
    campaign_id: str,
    body: ReasonIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("campaigns:write"))],
) -> CampaignView:
    view = deps.campaigns.resume(campaign_id, principal.actor, body.reason)
    _audit(deps, db, principal, "campaign.resume", f"campaign:{campaign_id}", body.reason)
    return view


class SimulateIn(_In):
    persona: str = Field(pattern=r"^C-[0-9]{2}$")
    seed: int = Field(ge=0, le=2**31 - 1)
    purpose: Purpose
    language: Language = "hinglish"


@router.post("/simulate", tags=["simulate"])
def simulate(
    body: SimulateIn, deps: Deps, _p: Annotated[Principal, Depends(require("simulate:run"))]
) -> SimulationResult:
    return deps.simulator.simulate(body.persona, body.seed, body.purpose, body.language)


@router.get("/incidents", tags=["incidents"])
def list_incidents(
    deps: Deps, _p: Annotated[Principal, Depends(require("incidents:read"))]
) -> list[IncidentView]:
    return deps.incidents.list_incidents()


class IncidentIn(_In):
    kind: IncidentKind
    summary: str = Field(min_length=3, max_length=2000)
    detected_at: datetime


@router.post("/incidents", tags=["incidents"])
def open_incident(
    body: IncidentIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("incidents:write"))],
) -> IncidentView:
    view = deps.incidents.open_incident(body.kind, body.summary, body.detected_at, principal.actor)
    _audit(deps, db, principal, "incident.open", f"incident:{view.incident_id}", body.kind)
    return view


@router.get("/audit", tags=["audit"])
def list_audit(
    deps: Deps,
    db: Db,
    _p: Annotated[Principal, Depends(require("audit:read"))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEvent]:
    rows = db.scalars(select(AuditRow).order_by(AuditRow.at.desc()).limit(limit))
    return [
        AuditEvent(
            schema_version="1.0.0",
            tenant_id=r.tenant_id,
            trace_id=r.trace_id,
            audit_id=r.audit_id,
            at=r.at,
            actor=r.actor,
            role=r.role,
            action=r.action,
            target=r.target,
            reason=r.reason,
        )
        for r in rows
    ]
