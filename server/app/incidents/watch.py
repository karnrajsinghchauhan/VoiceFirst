"""Pages a person when a CERT-In or DPDP report clock has run out (review R2 H2).

Runs every 15 minutes as a CronJob (deploy/helm cronjob-incident-watch.yaml). Each overdue
incident is paged once; the page stays open until a person acknowledges it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.incidents.models import IncidentRow
from app.incidents.service import overdue, page_human


def _page_text(row: IncidentRow) -> str:
    return f"OVERDUE {row.kind} report for incident {row.incident_id} (due {row.report_due_at:%Y-%m-%d %H:%M} UTC)"


def page_overdue(session: Session, tenant_id: str, now: datetime) -> int:
    already = set(session.scalars(select(IncidentRow.summary).where(IncidentRow.kind == "page")))
    paged = 0
    for row in overdue(session, tenant_id, now):
        text = _page_text(row)
        if text in already:
            continue
        page_human(session, tenant_id=tenant_id, summary=text, at=now, severity="sev1")
        paged += 1
    return paged


def main() -> None:
    from app.core.clock import SystemClock
    from app.core.config import get_settings
    from app.core.db import make_engine, make_session_factory, transaction
    from app.core.logging import configure_logging, get_logger

    configure_logging()
    settings = get_settings()
    factory = make_session_factory(make_engine(settings.database_url, settings.tenant_id))
    with transaction(factory) as session:
        paged = page_overdue(session, settings.tenant_id, SystemClock().now())
    get_logger(__name__).info("incident watch", extra={"paged": paged})


if __name__ == "__main__":
    main()
