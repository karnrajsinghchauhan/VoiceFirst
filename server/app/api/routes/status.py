"""GET /status: the public status page's data, from live checks (brief v3 S8).

Public and unauthenticated, so it names components and states only: no counts, ids or data.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import Deps
from app.compliance.killswitch import is_engaged
from app.core.db import transaction

router = APIRouter()
log = logging.getLogger(__name__)

State = Literal["operational", "degraded", "down"]


class Component(BaseModel):
    name: str
    status: State
    checked_at: datetime


class StatusReport(BaseModel):
    overall: State
    components: list[Component]
    # No uptime store exists yet; an empty history is the honest answer.
    history: list[dict[str, str | float]]


def _database_and_dialling(deps: Deps, now: datetime) -> list[Component]:
    try:
        with transaction(deps.session_factory) as s:
            s.execute(text("SELECT 1"))
            engaged = is_engaged(s, deps.settings.tenant_id)
    except SQLAlchemyError:
        # A status check reports the failure instead of raising it; the cause goes to the log.
        log.exception("status: database check failed")
        return [
            Component(name="Database", status="down", checked_at=now),
            Component(name="Outbound dialling", status="down", checked_at=now),
        ]
    dialling: State = "degraded" if engaged else "operational"
    return [
        Component(name="Database", status="operational", checked_at=now),
        Component(
            name="Outbound dialling (kill switch released)"
            if not engaged
            else "Outbound dialling (kill switch engaged)",
            status=dialling,
            checked_at=now,
        ),
    ]


@router.get("/status", tags=["ops"])
def status(deps: Deps) -> StatusReport:
    now = datetime.now(UTC)
    components = [Component(name="API", status="operational", checked_at=now)]
    components += _database_and_dialling(deps, now)
    s = deps.settings
    mocks = [
        role
        for role in ("stt", "tts", "llm", "telephony", "whatsapp", "crm")
        if getattr(s, role) == "mock"
    ]
    components.append(
        Component(
            name="Providers: test doubles (no live calls)" if mocks else "Providers: live",
            status="operational",
            checked_at=now,
        )
    )
    states = {c.status for c in components}
    overall: State = (
        "down" if "down" in states else "degraded" if "degraded" in states else "operational"
    )
    return StatusReport(overall=overall, components=components, history=[])
