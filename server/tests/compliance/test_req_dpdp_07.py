"""REQ-DPDP-07: retention by purpose; nightly purge logs counts. Time-travel tests."""

import logging
from datetime import timedelta

from app.core.clock import FrozenClock
from app.core.config import RetentionSettings
from app.postcall.crypto import DataCipher
from app.postcall.models import AudioRefRow, TranscriptRow
from app.postcall.retention import purge_expired
from app.postcall.settings import DEV_DATA_KEY
from app.postcall.store import TranscriptTurn, store_audio_ref, store_transcript


def _seed(session, at, call_id):
    cipher = DataCipher(DEV_DATA_KEY)
    store_transcript(
        session,
        cipher,
        tenant_id="agoda-in",
        call_id=call_id,
        phone_hash="ph",
        at=at,
        turns=[TranscriptTurn("agent", "hi")],
    )
    store_audio_ref(
        session, cipher, tenant_id="agoda-in", call_id=call_id, phone_hash="ph", at=at, uri="s3://x"
    )


def test_defaults_are_30_and_180_days():
    r = RetentionSettings()
    assert (r.audio_days, r.transcript_days) == (30, 180)


def test_time_travel_purge(session, clock, caplog):
    start = clock.now()
    _seed(session, start, "old")
    _seed(session, start + timedelta(days=100), "mid")
    later = FrozenClock(start + timedelta(days=180, seconds=1))
    with caplog.at_level(logging.INFO):
        counts = purge_expired(session, RetentionSettings(), later)
    # "old" is past both windows; "mid" (80 days) is past audio only.
    assert (counts.audio, counts.transcripts) == (2, 1)
    assert {r.call_id for r in session.query(TranscriptRow)} == {"mid"}
    assert session.query(AudioRefRow).count() == 0
    record = next(r for r in caplog.records if r.getMessage() == "retention purge")
    assert record.audio_purged == 2 and record.transcripts_purged == 1


def test_boundary_is_exclusive(session, clock):
    _seed(session, clock.now(), "c")
    exact = FrozenClock(clock.now() + timedelta(days=30))
    assert purge_expired(session, RetentionSettings(), exact).audio == 0
    exact.advance(timedelta(seconds=1))
    assert purge_expired(session, RetentionSettings(), exact).audio == 1


def test_configurable_per_purpose(session, clock):
    _seed(session, clock.now(), "c")
    short = RetentionSettings(audio_days=1, transcript_days=2)
    counts = purge_expired(session, short, FrozenClock(clock.now() + timedelta(days=3)))
    assert (counts.audio, counts.transcripts) == (1, 1)
