"""M4: 1,000 seeded bookings through the dispatcher over two simulated days.

About 100 held out, zero held-out dials, zero gate violations (every dial has a
fully passed gate decision and a consumed clearance), attempt caps and the
24 h per-number cooldown honoured.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.campaigns.models import HoldoutMemberRow, QueueItemRow
from app.campaigns.seed_data import build_seed
from app.compliance.holdout import is_held_out
from app.compliance.models import ClearanceRow, DialAttemptRow, GateDecisionRow
from app.core.db import transaction
from tests.campaigns.m4 import run_campaign

IST = ZoneInfo("Asia/Kolkata")


def test_m4_thousand_bookings(session_factory, bus, settings, clock):
    plan = build_seed(settings, count=1000, seed=2026, now=clock.now())
    run = run_campaign(session_factory, bus, settings, clock, plan, days=2)

    by_bucket = sum(
        is_held_out(settings.holdout.experiment_salt, e.booking_id, settings.holdout.percent)
        for e in plan.events
    )
    assert 85 <= by_bucket <= 115

    with transaction(session_factory) as s:
        attempts = list(s.scalars(select(DialAttemptRow)))
        decisions = {d.decision_id: d for d in s.scalars(select(GateDecisionRow))}
        clearances = {c.clearance_id: c for c in s.scalars(select(ClearanceRow))}
        held = set(s.scalars(select(HoldoutMemberRow.booking_id)))
        states = Counter(s.scalars(select(QueueItemRow.state)))

    # Every queued booking in the holdout bucket was recorded; none was dialled.
    assert held
    assert held.isdisjoint({a.booking_id for a in attempts})

    # Zero gate violations.
    for a in attempts:
        clearance = clearances[a.clearance_id]
        assert clearance.consumed_at == a.dialled_at
        decision = decisions[clearance.decision_id]
        assert decision.clearance_id == clearance.clearance_id
        assert all(g["passed"] for g in decision.gates)
        local = a.dialled_at.astimezone(IST).time()
        assert local.hour >= 9 and local.hour < 21
    assert len(run.telephony.placed) == len(attempts)

    # Attempt cap per event and cooldown per number.
    per_event = Counter(a.booking_event_id for a in attempts)
    assert max(per_event.values()) <= settings.compliance.max_attempts_per_event
    per_phone: dict[str, list] = defaultdict(list)
    for a in attempts:
        per_phone[a.phone_hash].append(a.dialled_at)
    for times in per_phone.values():
        times.sort()
        assert all(b - a >= timedelta(hours=24) for a, b in pairwise(times))

    # Second attempts happened, so the cap and cooldown were actually exercised.
    assert any(n == 2 for n in per_event.values())
    assert len(run.fallback.sent) == len(set(run.fallback.sent))
    assert states["blocked"] > 0  # DND numbers
    assert states["done"] > 0
    print(
        f"M4: events={len(plan.events)} held_out_recorded={len(held)} bucket_held={by_bucket} "
        f"dials={len(attempts)} states={dict(states)} fallbacks={len(run.fallback.sent)}"
    )
