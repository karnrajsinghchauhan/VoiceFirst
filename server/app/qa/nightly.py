"""Nightly QA job: score every call not yet scored. Clustering reads the scores weekly."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.generated.call_outcome import CallOutcome
from app.costs.book import CostBook
from app.postcall.crypto import DataCipher
from app.postcall.models import CallOutcomeRow
from app.postcall.store import read_transcript
from app.qa.scorecard import QaScoreRow, save_score, score_call


def score_unscored(
    session: Session, cipher: DataCipher, book: CostBook, tenant_id: str, at: datetime
) -> int:
    scored = select(QaScoreRow.call_id)
    rows = session.scalars(
        select(CallOutcomeRow).where(
            CallOutcomeRow.tenant_id == tenant_id, CallOutcomeRow.call_id.not_in(scored)
        )
    )
    count = 0
    for row in rows:
        outcome = CallOutcome.model_validate(row.payload)
        turns = read_transcript(session, cipher, row.call_id)
        save_score(session, tenant_id, score_call(outcome, turns, book), at)
        count += 1
    return count
