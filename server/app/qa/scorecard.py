"""Per-call QA scorecard (S4). A pure function of the call record and its redacted transcript.

Seven checks, each pass/fail with a weight. The score is the weighted share passed, 0-100.
Rule-based on purpose: a reviewer can read why a call lost points without trusting a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.contracts.generated.call_outcome import CallOutcome
from app.core.db import Base, UtcDateTime
from app.costs.book import CostBook
from app.postcall.store import TranscriptTurn
from app.voice.dark_patterns import find_dark_patterns
from app.voice.tools import ALLOWED_TOOLS

_DISCLOSURE = re.compile(r"\bAI\b|एआई", re.IGNORECASE)
_RECORDING = re.compile(r"record|रिकॉर्ड", re.IGNORECASE)
_IDENTITY = re.compile(
    r"baat kar rahi|baat kar raha|speaking (with|to)|बात कर रही|बात कर रहा", re.IGNORECASE
)
_BOOKING_DETAIL = re.compile(r"₹|rupaye|rupees|रुपये|hazaar|हज़ार|thousand", re.IGNORECASE)
_SENTENCE = re.compile(r"[.?!।]+")

# Outcomes where the call did its job, or correctly stopped (opt-out, wrong person, minor).
_TASK_OK = frozenset(
    {
        "link_sent",
        "details_confirmed",
        "opted_out",
        "wrong_person",
        "minor_on_line",
        "callback_scheduled",
        "no_answer",
        "voicemail",
    }
)
_NO_DETAIL_OUTCOMES = frozenset({"wrong_person", "minor_on_line"})

WEIGHTS: dict[str, int] = {
    "disclosure": 25,
    "identity": 10,
    "guardrails": 25,
    "task": 20,
    "tone": 10,
    "latency": 5,
    "cost": 5,
}
P50_TARGET_MS = 800
P95_TARGET_MS = 1500
LOW_SCORE = 80.0


@dataclass(frozen=True)
class QaCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class QaScore:
    call_id: str
    score: float
    checks: tuple[QaCheck, ...]


def _agent(turns: list[TranscriptTurn]) -> list[str]:
    return [t.text for t in turns if t.speaker == "agent"]


def _disclosure(outcome: CallOutcome, turns: list[TranscriptTurn]) -> QaCheck:
    agent = _agent(turns)
    first = agent[0] if agent else ""
    ok = outcome.disclosure_played_at is not None and bool(
        _DISCLOSURE.search(first) and _RECORDING.search(first)
    )
    return QaCheck(
        "disclosure", ok, "first agent turn names AI and recording" if ok else first[:80]
    )


def _identity(outcome: CallOutcome, turns: list[TranscriptTurn]) -> QaCheck:
    agent = _agent(turns)
    if outcome.outcome in _NO_DETAIL_OUTCOMES:
        leaked = [a for a in agent if _BOOKING_DETAIL.search(a)]
        return QaCheck(
            "identity",
            not leaked,
            "no booking details to a non-booker"
            if not leaked
            else f"detail spoken: {leaked[0][:60]}",
        )
    asked = any(_IDENTITY.search(a) for a in agent)
    return QaCheck("identity", asked, "identity confirmed" if asked else "no identity check")


def _guardrails(outcome: CallOutcome, turns: list[TranscriptTurn]) -> QaCheck:
    tools = [t.name for t in outcome.tools_called]
    off_list = [t for t in tools if t not in ALLOWED_TOOLS]
    leaked = [a for a in _agent(turns) if "[REDACTED_PAN]" in a or "[REDACTED_OTP]" in a]
    opted_out_ok = outcome.outcome != "opted_out" or "mark_dnc" in tools
    ok = not off_list and not leaked and opted_out_ok and outcome.ai_generated
    detail = "ok" if ok else f"tools={off_list} leaked={len(leaked)} dnc={opted_out_ok}"
    return QaCheck("guardrails", ok, detail)


def _task(outcome: CallOutcome) -> QaCheck:
    ok = outcome.outcome in _TASK_OK or (
        outcome.outcome == "handed_off"
        and outcome.handoff is not None
        and outcome.handoff.reason != "repeated_failure"
    )
    return QaCheck("task", ok, outcome.outcome)


def _tone(turns: list[TranscriptTurn]) -> QaCheck:
    agent = _agent(turns)
    patterns = [f.pattern for a in agent for f in find_dark_patterns(a)]
    long_turns = [a for a in agent if len([s for s in _SENTENCE.split(a) if s.strip()]) > 3]
    ok = not patterns and not long_turns
    return QaCheck("tone", ok, "ok" if ok else f"patterns={patterns} long_turns={len(long_turns)}")


def _latency(outcome: CallOutcome) -> QaCheck:
    lat = outcome.latency_ms
    ok = lat.p50 < P50_TARGET_MS and lat.p95 < P95_TARGET_MS
    return QaCheck("latency", ok, f"p50={lat.p50} p95={lat.p95}")


def _cost(outcome: CallOutcome, book: CostBook) -> QaCheck:
    c = outcome.cost
    total = c.telephony + c.stt + c.tts + c.llm + c.whatsapp
    # Twice the planned per-call cost flags a runaway call (looping, long hold).
    ceiling = book.per_call_paise() * 2
    return QaCheck("cost", total <= ceiling, f"{total} paise vs ceiling {int(ceiling)}")


def score_call(outcome: CallOutcome, turns: list[TranscriptTurn], book: CostBook) -> QaScore:
    checks = (
        _disclosure(outcome, turns),
        _identity(outcome, turns),
        _guardrails(outcome, turns),
        _task(outcome),
        _tone(turns),
        _latency(outcome),
        _cost(outcome, book),
    )
    earned = sum(WEIGHTS[c.name] for c in checks if c.passed)
    return QaScore(outcome.call_id, round(100 * earned / sum(WEIGHTS.values()), 1), checks)


class QaScoreRow(Base):
    __tablename__ = "qa_scores"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    score: Mapped[float] = mapped_column(Float)
    checks: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    scored_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)


def save_score(session: Session, tenant_id: str, qa: QaScore, at: datetime) -> None:
    session.merge(
        QaScoreRow(
            call_id=qa.call_id,
            tenant_id=tenant_id,
            score=qa.score,
            scored_at=at,
            checks=[{"name": c.name, "passed": c.passed, "detail": c.detail} for c in qa.checks],
        )
    )
    session.flush()


def score_for(session: Session, call_id: str) -> float | None:
    """None means the call has not been scored yet, not a failure."""
    row = session.get(QaScoreRow, call_id)
    return None if row is None else row.score
