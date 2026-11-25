"""J3 holdout proofs (11.4): 100 +/- 15 of 1,000, zero held-out dials, same bucket across processes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select

from app.campaigns.models import HoldoutMemberRow
from app.campaigns.seed_data import build_seed
from app.compliance.holdout import bucket, is_held_out
from app.compliance.models import DialAttemptRow
from app.core.db import transaction
from tests.campaigns.m4 import run_campaign

SERVER = Path(__file__).resolve().parents[2]


def _ids(n: int) -> list[str]:
    return [f"AGD{i:07d}" for i in range(n)]


def test_thousand_bookings_hold_out_about_a_hundred(settings):
    held = sum(
        is_held_out(settings.holdout.experiment_salt, b, settings.holdout.percent)
        for b in _ids(1000)
    )
    assert 85 <= held <= 115


def test_bucket_formula_matches_brief():
    import hashlib

    expected = int(hashlib.sha256(b"salt" + b"AGD0000001").hexdigest(), 16) % 100
    assert bucket("salt", "AGD0000001") == expected


def test_bucket_is_identical_in_another_process(settings):
    ids = _ids(200)
    code = (
        "import json,sys; from app.compliance.holdout import bucket; "
        "ids=json.loads(sys.argv[2]); print(json.dumps([bucket(sys.argv[1], b) for b in ids]))"
    )
    out = subprocess.run(  # noqa: S603 - fixed argv built from this test
        [sys.executable, "-c", code, settings.holdout.experiment_salt, json.dumps(ids)],
        cwd=SERVER,
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONHASHSEED": "random", "PATH": ""},
    )
    assert json.loads(out.stdout) == [bucket(settings.holdout.experiment_salt, b) for b in ids]


def test_no_held_out_booking_is_ever_dialled(session_factory, bus, settings, clock):
    plan = build_seed(settings, count=1000, seed=7, now=clock.now())
    run_campaign(session_factory, bus, settings, clock, plan, days=2)
    with transaction(session_factory) as s:
        held = set(s.scalars(select(HoldoutMemberRow.booking_id)))
        dialled = set(s.scalars(select(DialAttemptRow.booking_id)))
    assert held
    assert held.isdisjoint(dialled)
    assert all(
        is_held_out(settings.holdout.experiment_salt, b, settings.holdout.percent) for b in held
    )
