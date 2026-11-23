"""Nightly retention purge (REQ-DPDP-07). Deletes by purpose-specific age and logs the counts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import RetentionSettings
from app.core.logging import get_logger
from app.postcall.models import AudioRefRow, TranscriptRow

_log = get_logger(__name__)


@dataclass(frozen=True)
class PurgeCounts:
    audio: int
    transcripts: int


def purge_expired(session: Session, retention: RetentionSettings, clock: Clock) -> PurgeCounts:
    now = clock.now()
    audio_cutoff = now - timedelta(days=retention.audio_days)
    transcript_cutoff = now - timedelta(days=retention.transcript_days)
    audio = session.execute(delete(AudioRefRow).where(AudioRefRow.created_at < audio_cutoff))
    transcripts = session.execute(
        delete(TranscriptRow).where(TranscriptRow.created_at < transcript_cutoff)
    )
    counts = PurgeCounts(audio=audio.rowcount, transcripts=transcripts.rowcount)
    _log.info(
        "retention purge",
        extra={"audio_purged": counts.audio, "transcripts_purged": counts.transcripts},
    )
    return counts
