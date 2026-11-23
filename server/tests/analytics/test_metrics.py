from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.analytics.lift import InsufficientSampleError
from app.analytics.metrics import (
    containment,
    containment_by,
    cost_per_resolved_contact_paise,
    csat,
    recovery_rate,
    resolution_time,
)
from app.analytics.queries import j1_arm_counts, j1_lift
from app.campaigns.models import BookingEventRow, QueueItemRow
from app.campaigns.seed_data import build_seed
from app.contracts.generated.call_outcome import CallOutcome
from app.costs.book import load_book
from tests.campaigns.m4 import run_campaign


def _outcome(name: str) -> CallOutcome:
    return CallOutcome.model_validate(
        {
            "schema_version": "1.0.0",
            "tenant_id": "agoda-in",
            "trace_id": "0" * 32,
            "call_id": "call_1",
            "clearance_id": "clr_1",
            "booking_id": "AGD0000001",
            "purpose": "J1",
            "cli": "+911600200001",
            "started_at": "2026-11-23T06:30:00Z",
            "answered": name != "no_answer",
            "amd_result": "human",
            "language_detected": "hi",
            "disclosure_played_at": None,
            "turns": 3,
            "tools_called": [],
            "outcome": name,
            "handoff": None,
            "latency_ms": {"p50": 1, "p95": 2},
            "cost": {"telephony": 100, "stt": 50, "tts": 50, "llm": 20, "whatsapp": 0},
            "redaction_applied": True,
            "sensitive_data_spoken": False,
            "grievance_channel": "g",
            "ai_generated": True,
            "model_ids": {},
            "provenance_hash": "0" * 64,
        }
    )


def _book():
    from tests.factories import make_settings

    return load_book(make_settings().costs_file)


def test_whatsapp_utility_includes_gst():
    assert _book().unit_paise("whatsapp") == Decimal("13.5700")


def test_containment_counts_only_reached_calls():
    outs = [_outcome(n) for n in ("link_sent", "handed_off", "no_answer", "voicemail")]
    assert containment(outs) == 0.5
    by = containment_by([("C-01", outs[0]), ("C-05", outs[1]), ("C-25", outs[2])])
    assert by == {"C-01": 1.0, "C-05": 0.0}


def test_cost_per_resolved_contact():
    outs = [_outcome("link_sent"), _outcome("no_answer")]
    assert cost_per_resolved_contact_paise(
        outs, whatsapp_templates_sent=2, book=_book()
    ) == Decimal("467.14")
    with pytest.raises(InsufficientSampleError):
        cost_per_resolved_contact_paise([_outcome("no_answer")], 0, _book())


def test_recovery_csat_resolution():
    assert recovery_rate([True, False, False, True]) == 0.5
    assert csat([5, 4, 3, 1]) == 0.5
    summary = resolution_time([timedelta(hours=h) for h in (1, 2, 3, 4, 10)])
    assert summary.median == timedelta(hours=3)
    assert summary.n == 5
    with pytest.raises(InsufficientSampleError):
        csat([6])
    with pytest.raises(InsufficientSampleError):
        recovery_rate([])


def test_lift_from_campaign_tables(session_factory, bus, settings, clock):
    plan = build_seed(settings, count=1000, seed=11, now=clock.now())
    run_campaign(session_factory, bus, settings, clock, plan, days=1)
    with session_factory() as s:
        before = j1_arm_counts(s, settings)
        assert before.n_control > 0 and before.n_treated > 0
        assert before.recovered_treated == 0 and before.recovered_control == 0
        with pytest.raises(InsufficientSampleError):
            j1_lift(s, settings)
        # Simulate payments: every link_sent booking pays; one in five of the rest pays anyway.
        items = s.scalars(select(QueueItemRow).where(QueueItemRow.purpose == "J1")).all()
        for n, item in enumerate(items):
            if item.last_outcome == "link_sent" or n % 5 == 0:
                s.add(
                    BookingEventRow(
                        event_id=f"paid_{item.booking_id}",
                        tenant_id=item.tenant_id,
                        booking_id=item.booking_id,
                        status="confirmed",
                        received_at=clock.now(),
                        payload={},
                    )
                )
        s.commit()
        result = j1_lift(s, settings)
    assert result.lift > 0 and result.significant
    assert result.ci_low > 0
