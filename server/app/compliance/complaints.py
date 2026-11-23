"""Complaint guardrail (REQ-TRAI-06, REQ-TRAI-10).

TRAI acts at 3+ unique complaints in 10 days against an AI-flagged CLI, or 5+
otherwise; first violation bars outgoing services for 15 days. Our house rule is
far stricter so we never get near that line:
- any complaint pauses the CLI it names;
- 2 unique complainants in a rolling 10 days pause every campaign and page a human.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.compliance.models import CampaignPauseRow, CliRow, ComplaintRow
from app.contracts.generated.complaint import Complaint
from app.core.bus import EventBus
from app.core.config import Settings
from app.core.ids import new_id
from app.incidents.service import page_human


@dataclass(frozen=True)
class ComplaintOutcome:
    cli_paused: bool
    campaigns_paused: bool
    unique_complainants_in_window: int
    trai_threshold_reached: bool


def _unique_complainants(session: Session, tenant_id: str, since: datetime) -> int:
    stmt = select(func.count(func.distinct(ComplaintRow.complainant_hash))).where(
        ComplaintRow.tenant_id == tenant_id, ComplaintRow.received_at >= since
    )
    return session.scalar(stmt) or 0


def _unique_for_cli(session: Session, cli_e164: str, since: datetime) -> int:
    stmt = select(func.count(func.distinct(ComplaintRow.complainant_hash))).where(
        ComplaintRow.cli_e164 == cli_e164, ComplaintRow.received_at >= since
    )
    return session.scalar(stmt) or 0


def _pause_cli(session: Session, cli_e164: str, complaint_id: str) -> bool:
    row = session.get(CliRow, cli_e164)
    if row is None:
        # A complaint about a number we never registered is still recorded; nothing to pause.
        return False
    row.status = "paused"
    row.paused_reason = f"complaint {complaint_id}"
    session.flush()
    return True


def _pause_all(session: Session, tenant_id: str, at: datetime, reason: str) -> None:
    active = session.scalar(
        select(func.count())
        .select_from(CampaignPauseRow)
        .where(CampaignPauseRow.tenant_id == tenant_id, CampaignPauseRow.lifted_at.is_(None))
    )
    if active:
        return
    session.add(
        CampaignPauseRow(
            pause_id=new_id("pause"),
            tenant_id=tenant_id,
            reason=reason,
            paused_at=at,
            lifted_at=None,
            lifted_by=None,
        )
    )
    session.flush()


def ingest_complaint(
    session: Session, bus: EventBus, settings: Settings, complaint: Complaint
) -> ComplaintOutcome:
    """Accepts DLT-forwarded complaints, including call-management-app spam reports."""
    session.add(
        ComplaintRow(
            complaint_id=complaint.complaint_id,
            tenant_id=complaint.tenant_id,
            cli_e164=complaint.cli_e164,
            complainant_hash=complaint.complainant_hash,
            received_at=complaint.received_at,
            source=complaint.source,
            ai_flagged=complaint.ai_flagged,
            dlt_ref=complaint.dlt_ref,
        )
    )
    session.flush()
    bus.publish("av.complaints.v1", complaint.cli_e164, complaint)
    since = complaint.received_at - timedelta(days=settings.compliance.complaint_window_days)
    cli_paused = _pause_cli(session, complaint.cli_e164, complaint.complaint_id)
    unique = _unique_complainants(session, complaint.tenant_id, since)
    pause_all = unique >= settings.compliance.complaints_pause_all
    if pause_all:
        reason = f"{unique} unique complaints in {settings.compliance.complaint_window_days} days"
        _pause_all(session, complaint.tenant_id, complaint.received_at, reason)
        page_human(
            session,
            tenant_id=complaint.tenant_id,
            at=complaint.received_at,
            severity="sev1",
            summary=f"complaint guardrail: {reason}; all campaigns paused",
        )
    per_cli = _unique_for_cli(session, complaint.cli_e164, since)
    trai_limit = 3 if complaint.ai_flagged else 5
    return ComplaintOutcome(
        cli_paused=cli_paused,
        campaigns_paused=pause_all,
        unique_complainants_in_window=unique,
        trai_threshold_reached=per_cli >= trai_limit,
    )


def lift_campaign_pause(session: Session, tenant_id: str, at: datetime, actor: str) -> None:
    rows = session.scalars(
        select(CampaignPauseRow).where(
            CampaignPauseRow.tenant_id == tenant_id, CampaignPauseRow.lifted_at.is_(None)
        )
    )
    for row in rows:
        row.lifted_at = at
        row.lifted_by = actor
    session.flush()
