"""Console data views: unit economics (/costs) and caller numbers (/numbers)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.admin.rbac import Principal
from app.api.deps import Db, Deps, require
from app.compliance.models import CliRow, ComplaintRow, DialAttemptRow
from app.costs.book import load_book
from app.postcall.models import CallOutcomeRow

router = APIRouter()


class CostComponentView(BaseModel):
    name: str
    unit: str
    unit_price: str
    source: str
    source_url: str | None
    checked_at: date
    per_minute_paise: str
    estimate: bool


class ComparisonView(BaseModel):
    vendor: str
    price: str
    currency: str
    unit: str
    source_url: str
    checked_at: date


class CostsView(BaseModel):
    as_of: date
    currency: str
    re_check_before_quoting: bool
    components: list[CostComponentView]
    per_minute_paise: str
    per_call_paise: str
    per_resolved_contact_paise: str
    assumptions: dict[str, str]
    comparison: list[ComparisonView]


def _q(amount: Decimal) -> str:
    # Two decimal places of a paisa: enough to show sub-paisa unit costs, never float noise.
    return str(amount.quantize(Decimal("0.01")))


@router.get("/costs", tags=["costs"])
def get_costs(deps: Deps, _p: Annotated[Principal, Depends(require("metrics:read"))]) -> CostsView:
    book = load_book(deps.settings.costs_file)
    return CostsView(
        as_of=book.as_of,
        currency=book.currency,
        re_check_before_quoting=book.re_check_before_quoting,
        components=[
            CostComponentView(
                name=c.name,
                unit=c.unit,
                unit_price=str(c.unit_price),
                source=c.source,
                source_url=c.source_url,
                checked_at=c.checked_at,
                per_minute_paise=_q(book.per_minute_paise(c.name)),
                estimate=c.estimate,
            )
            for c in book.components
        ],
        per_minute_paise=_q(book.total_per_minute_paise()),
        per_call_paise=_q(book.per_call_paise()),
        per_resolved_contact_paise=_q(book.per_resolved_contact_paise()),
        assumptions={k: str(v) for k, v in book.assumptions.model_dump().items()},
        comparison=[ComparisonView(**c.model_dump()) for c in book.comparison],
    )


class NumberView(BaseModel):
    cli_e164: str
    series: str
    purpose: str
    oap: str
    declaration_ref: str | None
    dlt_recorded_at: datetime | None
    status: str
    complaints_10d: int
    answer_rate: float | None
    auto_paused: bool
    paused_reason: str | None


@router.get("/numbers", tags=["numbers"])
def list_numbers(
    deps: Deps, db: Db, _p: Annotated[Principal, Depends(require("cli:read"))]
) -> list[NumberView]:
    since = deps.clock.now() - timedelta(days=deps.settings.compliance.complaint_window_days)
    out: list[NumberView] = []
    for row in db.scalars(select(CliRow).order_by(CliRow.cli_e164)):
        complaints = (
            db.scalar(
                select(func.count())
                .select_from(ComplaintRow)
                .where(ComplaintRow.cli_e164 == row.cli_e164, ComplaintRow.received_at >= since)
            )
            or 0
        )
        dialled = (
            db.scalar(
                select(func.count())
                .select_from(DialAttemptRow)
                .where(DialAttemptRow.cli_e164 == row.cli_e164)
            )
            or 0
        )
        answered = (
            db.scalar(
                select(func.count())
                .select_from(CallOutcomeRow)
                .join(DialAttemptRow, DialAttemptRow.call_id == CallOutcomeRow.call_id)
                .where(
                    DialAttemptRow.cli_e164 == row.cli_e164,
                    CallOutcomeRow.outcome.not_in(("no_answer", "voicemail")),
                )
            )
            or 0
        )
        out.append(
            NumberView(
                cli_e164=row.cli_e164,
                series=row.series,
                purpose=row.purpose,
                oap=row.oap,
                declaration_ref=row.declaration_ref,
                dlt_recorded_at=row.dlt_recorded_at,
                status=row.status,
                complaints_10d=complaints,
                answer_rate=answered / dialled if dialled else None,
                # The complaint guardrail is the only automatic pauser; it names the complaint.
                auto_paused=row.status == "paused"
                and (row.paused_reason or "").startswith("complaint"),
                paused_reason=row.paused_reason,
            )
        )
    return out
