"""Record endpoints: calls, consent, CLI registry, handoff."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.admin.rbac import Principal
from app.api.deps import Db, Deps, require
from app.api.ports import TranscriptLine
from app.api.types import IsoDatetime, StrictBool
from app.compliance import consent as consent_api
from app.compliance.models import CliRow
from app.contracts.generated.call_outcome import CallOutcome
from app.contracts.generated.cli import Cli
from app.contracts.generated.consent_record import ConsentRecord
from app.contracts.generated.handoff_summary import HandoffSummary
from app.core.audit import write_audit
from app.core.ids import new_trace_id
from app.core.types import Purpose
from app.handoff import transfer
from app.postcall import store

router = APIRouter()

_E164 = r"^\+[1-9][0-9]{6,14}$"


class _In(BaseModel):
    # Strict: a request that violates the documented schema is refused, never coerced.
    model_config = ConfigDict(extra="forbid")


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


@router.get("/calls", tags=["calls"])
def list_calls(
    db: Db,
    _p: Annotated[Principal, Depends(require("calls:read"))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CallOutcome]:
    return store.list_outcomes(db, limit)


@router.get("/calls/{call_id}", tags=["calls"])
def get_call(
    call_id: str, db: Db, _p: Annotated[Principal, Depends(require("calls:read"))]
) -> CallOutcome:
    return store.get_outcome(db, call_id)


@router.get("/calls/{call_id}/transcript", tags=["calls"])
def get_transcript(
    call_id: str,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("transcripts:read"))],
) -> list[TranscriptLine]:
    turns = store.read_transcript(db, deps.cipher, call_id)
    # Reading a transcript is a privileged action even though it is redacted.
    _audit(deps, db, principal, "transcript.read", f"call:{call_id}", "console view")
    return [TranscriptLine(speaker=t.speaker, text=t.text) for t in turns]


class ConsentIn(_In):
    phone_e164: str = Field(pattern=_E164)
    basis: Literal["transaction", "explicit", "inquiry"]
    purpose: Purpose
    channel: Literal["voice", "whatsapp", "sms", "web", "dca"]
    booking_id: str | None = Field(default=None, min_length=4)
    source_ref: str = Field(min_length=1)
    evidence_uri: str | None = None


@router.post("/consent", tags=["consent"])
def record_consent(
    body: ConsentIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("consent:write"))],
) -> ConsentRecord:
    record = consent_api.record_consent(
        db,
        deps.settings,
        phone_e164=body.phone_e164,
        basis=body.basis,
        purpose=body.purpose,
        channel=body.channel,
        obtained_at=deps.clock.now(),
        booking_id=body.booking_id,
        source_ref=body.source_ref,
        trace_id=new_trace_id(),
        evidence_uri=body.evidence_uri,
    )
    _audit(deps, db, principal, "consent.record", f"consent:{record.consent_id}", body.basis)
    return record


class PhoneIn(_In):
    phone_e164: str = Field(pattern=_E164)


@router.post("/consent/lookup", tags=["consent"])
def lookup_consent(
    body: PhoneIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("consent:read"))],
) -> list[ConsentRecord]:
    # POST so the number never lands in access logs as a query string.
    records = consent_api.consents_for(db, body.phone_e164)
    _audit(deps, db, principal, "consent.lookup", "consent:lookup", "evidence review")
    return records


class OptOutIn(_In):
    phone_e164: str = Field(pattern=_E164)
    channel: Literal["voice", "whatsapp", "sms", "web", "dca"]


@router.post("/consent/opt-out", tags=["consent"])
def opt_out(
    body: OptOutIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("consent:write"))],
) -> list[ConsentRecord]:
    consent_api.mark_dnc(
        db,
        deps.settings,
        phone_e164=body.phone_e164,
        at=deps.clock.now(),
        channel=body.channel,
        call_id=None,
    )
    _audit(deps, db, principal, "consent.opt_out", "consent:opt_out", body.channel)
    return consent_api.consents_for(db, body.phone_e164)


def _cli_view(row: CliRow) -> Cli:
    return Cli(
        schema_version="1.0.0",
        tenant_id=row.tenant_id,
        trace_id=new_trace_id(),
        cli_e164=row.cli_e164,
        series=row.series,
        purpose=row.purpose,
        oap=row.oap,
        a2p_declared=row.a2p_declared,
        declaration_ref=row.declaration_ref,
        dlt_recorded_at=row.dlt_recorded_at,
        status=row.status,
        paused_reason=row.paused_reason,
    )


@router.get("/cli", tags=["cli"])
def list_cli(db: Db, _p: Annotated[Principal, Depends(require("cli:read"))]) -> list[Cli]:
    return [_cli_view(r) for r in db.scalars(select(CliRow).order_by(CliRow.cli_e164))]


class CliIn(_In):
    series: Literal["140", "1600", "1601"]
    purpose: Literal["service", "transactional", "promotional"]
    oap: str = Field(min_length=1)
    a2p_declared: StrictBool
    declaration_ref: str | None = None
    dlt_recorded_at: IsoDatetime | None = None
    status: Literal["active", "paused", "retired"]
    paused_reason: str | None = None


@router.put("/cli/{cli_e164}", tags=["cli"])
def upsert_cli(
    cli_e164: Annotated[str, Path(pattern=_E164)],
    body: CliIn,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("cli:write"))],
) -> Cli:
    row = CliRow(cli_e164=cli_e164, tenant_id=deps.settings.tenant_id, **body.model_dump())
    merged = db.merge(row)
    db.flush()
    _audit(deps, db, principal, "cli.upsert", f"cli:{cli_e164}", body.status)
    return _cli_view(merged)


class HandoffView(BaseModel):
    call_id: str
    result: Literal["transferred", "callback_scheduled"]
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    crm_ticket_id: str | None
    summary: HandoffSummary


@router.get("/handoff", tags=["handoff"])
def list_handoffs(
    db: Db,
    _p: Annotated[Principal, Depends(require("handoff:read"))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[HandoffView]:
    return [
        HandoffView(
            call_id=r.call_id,
            result=r.result,
            created_at=r.created_at,
            acknowledged_at=r.acknowledged_at,
            resolved_at=r.resolved_at,
            crm_ticket_id=r.crm_ticket_id,
            summary=HandoffSummary.model_validate(r.summary),
        )
        for r in transfer.list_open(db, limit)
    ]


@router.get("/handoff/{call_id}", tags=["handoff"])
def get_handoff(
    call_id: str, db: Db, _p: Annotated[Principal, Depends(require("handoff:read"))]
) -> HandoffSummary:
    return transfer.get_summary(db, call_id)


class HandoffAction(_In):
    action: Literal["acknowledge", "resolve"]


@router.post("/handoff/{call_id}", tags=["handoff"])
def act_on_handoff(
    call_id: str,
    body: HandoffAction,
    deps: Deps,
    db: Db,
    principal: Annotated[Principal, Depends(require("handoff:write"))],
) -> HandoffSummary:
    step = transfer.acknowledge if body.action == "acknowledge" else transfer.resolve
    step(db, call_id, deps.clock.now())
    _audit(deps, db, principal, f"handoff.{body.action}", f"call:{call_id}", body.action)
    return transfer.get_summary(db, call_id)
