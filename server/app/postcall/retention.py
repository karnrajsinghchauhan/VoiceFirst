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
from app.rights.scrub import ScrubCounts, scrub_older_than

_log = get_logger(__name__)


@dataclass(frozen=True)
class PurgeCounts:
    audio: int
    transcripts: int
    personal_fields: ScrubCounts


def purge_expired(session: Session, retention: RetentionSettings, clock: Clock) -> PurgeCounts:
    now = clock.now()
    audio_cutoff = now - timedelta(days=retention.audio_days)
    transcript_cutoff = now - timedelta(days=retention.transcript_days)
    audio = session.execute(delete(AudioRefRow).where(AudioRefRow.created_at < audio_cutoff))
    transcripts = session.execute(
        delete(TranscriptRow).where(TranscriptRow.created_at < transcript_cutoff)
    )
    # Booking payloads, clearances and handoff summaries keep names and numbers; they go
    # with the transcripts, the longest purpose-bound retention (review R2 H1).
    scrubbed = scrub_older_than(session, transcript_cutoff)
    counts = PurgeCounts(
        audio=audio.rowcount, transcripts=transcripts.rowcount, personal_fields=scrubbed
    )
    _log.info(
        "retention purge",
        extra={
            "audio_purged": counts.audio,
            "transcripts_purged": counts.transcripts,
            "booking_events_scrubbed": scrubbed.booking_events,
            "clearances_scrubbed": scrubbed.clearances,
            "handoffs_scrubbed": scrubbed.handoffs,
        },
    )
    return counts


def main() -> None:
    """Nightly CronJob entry point (deploy/helm cronjob-retention.yaml)."""
    from app.core.clock import SystemClock
    from app.core.config import get_settings
    from app.core.db import make_engine, make_session_factory, transaction
    from app.core.logging import configure_logging

    configure_logging()
    settings = get_settings()
    with transaction(
        make_session_factory(make_engine(settings.database_url, settings.tenant_id))
    ) as session:
        purge_expired(session, settings.retention, SystemClock())


if __name__ == "__main__":
    main()
