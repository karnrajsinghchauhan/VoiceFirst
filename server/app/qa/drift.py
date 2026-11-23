"""Week-on-week metric drift alert (S4). Pages a human; it never changes behaviour on its own."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.incidents.service import page_human

Metric = Literal["containment", "csat", "complaint_rate", "p95_latency_ms"]


@dataclass(frozen=True)
class WeekMetrics:
    containment: float
    csat: float | None
    complaint_rate: float
    p95_latency_ms: int


@dataclass(frozen=True)
class DriftThresholds:
    """Absolute moves that page. Containment and CSAT alert on drops; the rest on rises."""

    containment_drop: float = 0.05
    csat_drop: float = 0.3
    complaint_rate_rise: float = 0.002
    p95_latency_rise_ms: int = 200


@dataclass(frozen=True)
class Drift:
    metric: Metric
    previous: float
    current: float


def find_drift(prev: WeekMetrics, cur: WeekMetrics, t: DriftThresholds) -> list[Drift]:
    out: list[Drift] = []
    if prev.containment - cur.containment > t.containment_drop:
        out.append(Drift("containment", prev.containment, cur.containment))
    if prev.csat is not None and cur.csat is not None and prev.csat - cur.csat > t.csat_drop:
        out.append(Drift("csat", prev.csat, cur.csat))
    if cur.complaint_rate - prev.complaint_rate > t.complaint_rate_rise:
        out.append(Drift("complaint_rate", prev.complaint_rate, cur.complaint_rate))
    if cur.p95_latency_ms - prev.p95_latency_ms > t.p95_latency_rise_ms:
        out.append(Drift("p95_latency_ms", prev.p95_latency_ms, cur.p95_latency_ms))
    return out


def alert_drift(session: Session, tenant_id: str, at: datetime, drifts: list[Drift]) -> None:
    for d in drifts:
        page_human(
            session,
            tenant_id=tenant_id,
            at=at,
            severity="sev2",
            summary=f"metric drift: {d.metric} moved {d.previous} -> {d.current} week on week",
        )
