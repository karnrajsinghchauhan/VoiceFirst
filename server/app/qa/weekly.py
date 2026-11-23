"""Weekly review (S4): top causes, examples, a proposed fix each, and draft fix PRs.

The review proposes; it never applies. Draft personas go to evals/personas/proposed/ (outside
the live eval suite) and PR descriptions to reports/fix-prs/<date>/. A human opens each PR,
the eval gate runs, and a named approver merges. Nothing here writes to voice/prompts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.generated.call_outcome import CallOutcome
from app.postcall.crypto import DataCipher
from app.postcall.models import CallOutcomeRow
from app.postcall.store import TranscriptTurn, read_transcript
from app.qa.cluster import Cause, Classified, classify, needs_review
from app.qa.scorecard import QaCheck, QaScore, QaScoreRow

PROPOSED_FIX: dict[Cause, str] = {
    "missed_opt_out": "Widen the opt-out lexicon in voice/guardrails.py to the phrasing in the "
    "examples; opt-out must win over every other signal.",
    "misheard_amount": "Treat an amount dispute as a money question: log_case and warm_transfer "
    "(P1), and read the amount back from the booking record only.",
    "wrong_language": "Switch to the language the customer asks for on the next turn "
    "(10.1 mirror by turn 2) instead of re-asking in the old language.",
    "customer_confusion": "Do not read confusion as refusal: explain once in plain words, "
    "then ask again; never end the call as declined after 'samajh nahi aaya'.",
    "slow_tool": "Profile the slow tool; keep one filler only; add a latency SLO alert on the tool.",
    "other": "Read the transcripts; no rule matched.",
}

# The behaviour each cause should have produced. A draft persona expects this, so it fails
# today and passes once the fix lands; that is what makes it a reproduction.
_EXPECT: dict[Cause, dict[str, Any]] = {
    "missed_opt_out": {"outcome": ["opted_out"], "tools_required": ["mark_dnc"]},
    "misheard_amount": {"outcome": ["handed_off"], "tools_required": ["warm_transfer"]},
    "wrong_language": {
        "outcome": ["link_sent", "declined", "callback_scheduled"],
        "handoff": False,
    },
    "customer_confusion": {"outcome": ["link_sent", "handed_off", "callback_scheduled"]},
}
PERSONA_REPRODUCIBLE: frozenset[Cause] = frozenset(_EXPECT)


@dataclass(frozen=True)
class CallRecord:
    outcome: CallOutcome
    turns: list[TranscriptTurn]
    qa: QaScore


@dataclass(frozen=True)
class CauseSummary:
    cause: Cause
    count: int
    examples: tuple[str, ...]
    evidence: tuple[str, ...]
    proposed_fix: str


@dataclass(frozen=True)
class Review:
    week_start: date
    calls: int
    reviewed: int
    top: tuple[CauseSummary, ...]
    classified: tuple[Classified, ...]


def _qa(row: QaScoreRow) -> QaScore:
    checks = tuple(QaCheck(str(c["name"]), bool(c["passed"]), str(c["detail"])) for c in row.checks)
    return QaScore(row.call_id, row.score, checks)


def load_week(session: Session, cipher: DataCipher, week_start: date) -> list[CallRecord]:
    start = datetime.combine(week_start, time(0), UTC)
    rows = session.scalars(
        select(CallOutcomeRow)
        .where(
            CallOutcomeRow.started_at >= start,
            CallOutcomeRow.started_at < start + timedelta(days=7),
        )
        .order_by(CallOutcomeRow.started_at)
    )
    records = []
    for row in rows:
        qa_row = session.get(QaScoreRow, row.call_id)
        if qa_row is None:
            continue  # unscored calls are picked up by the next nightly run
        records.append(
            CallRecord(
                CallOutcome.model_validate(row.payload),
                read_transcript(session, cipher, row.call_id),
                _qa(qa_row),
            )
        )
    return records


def build_review(records: list[CallRecord], week_start: date) -> Review:
    flagged = [classify(r.outcome, r.turns) for r in records if needs_review(r.outcome, r.qa)]
    counts = Counter(c.cause for c in flagged)
    top = tuple(
        CauseSummary(
            cause=cause,
            count=n,
            examples=tuple(c.call_id for c in flagged if c.cause == cause)[:3],
            evidence=tuple(c.evidence for c in flagged if c.cause == cause)[:3],
            proposed_fix=PROPOSED_FIX[cause],
        )
        for cause, n in counts.most_common(5)
    )
    return Review(week_start, len(records), len(flagged), top, tuple(flagged))


def render_review(review: Review) -> str:
    lines = [
        f"# Weekly review: week of {review.week_start.isoformat()}",
        "",
        f"Calls scored: {review.calls}. Flagged for review (failed, a promise check failed, or QA score below 80): "
        f"{review.reviewed}.",
        "Transcripts are redacted; call ids open the access-controlled transcript in the console.",
        "Each fix below is a proposal. It ships only as a PR that passes the eval gate and is "
        "approved by a named human.",
        "",
    ]
    for i, s in enumerate(review.top, 1):
        lines += [
            f"## {i}. {s.cause.replace('_', ' ')} ({s.count} calls)",
            "",
            f"- Example calls: {', '.join(s.examples)}",
            *[f'- Evidence: "{e}"' for e in s.evidence],
            f"- Proposed fix: {s.proposed_fix}",
            "",
        ]
    return "\n".join(lines)


@dataclass(frozen=True)
class DraftFix:
    cause: Cause
    branch: str
    persona_path: Path
    pr_path: Path


def _persona(cause: Cause, record: CallRecord, persona_id: str) -> dict[str, Any]:
    language = record.outcome.language_detected
    lang = "hinglish" if language == "unknown" else language
    lines = [t.text for t in record.turns if t.speaker == "customer"] or ["haan"]
    return {
        "id": persona_id,
        "title": f"reproduces {cause.replace('_', ' ')} from call {record.outcome.call_id}",
        "journey": record.outcome.purpose,
        "languages": [lang],
        "preferred_language": lang,
        "turns": {lang: [[line] for line in lines]},
        "default": {lang: lines[-1]},
        "expect": _EXPECT[cause],
        "hidden_facts": [f"drafted by the weekly review; source call {record.outcome.call_id}"],
    }


def draft_fixes(
    review: Review, records: list[CallRecord], root: Path, n: int = 3
) -> list[DraftFix]:
    by_id = {r.outcome.call_id: r for r in records}
    stamp = review.week_start.isoformat()
    out: list[DraftFix] = []
    for s in [s for s in review.top if s.cause in PERSONA_REPRODUCIBLE][:n]:
        persona_id = f"C-9{len(out) + 1:02d}"
        record = by_id[s.examples[0]]
        persona_path = root / "evals/personas/proposed" / f"{persona_id}.yaml"
        persona_path.parent.mkdir(parents=True, exist_ok=True)
        persona_path.write_text(
            yaml.safe_dump(
                _persona(s.cause, record, persona_id), allow_unicode=True, sort_keys=False
            )
        )
        branch = f"fix/qa-{stamp}-{s.cause.replace('_', '-')}"
        pr_path = root / "reports/fix-prs" / stamp / f"{branch.replace('/', '_')}.md"
        pr_path.parent.mkdir(parents=True, exist_ok=True)
        pr_path.write_text(
            "\n".join(
                [
                    f"# Fix: {s.cause.replace('_', ' ')} (weekly review {stamp})",
                    "",
                    f"Branch: `{branch}`",
                    "",
                    "## Why",
                    f"{s.count} calls in the week of {stamp} failed for this cause.",
                    f"Example calls: {', '.join(s.examples)}.",
                    "",
                    "## Proposed change",
                    s.proposed_fix,
                    "",
                    "## Reproduction",
                    f"`{persona_path.relative_to(root)}` fails on main today. Move it into "
                    "evals/personas/ with the fix; it must pass, and every existing persona must still "
                    "pass the eval gate (brief 11.9).",
                    "",
                    "## Approval",
                    "Drafted automatically by the weekly review. Not applied. Needs a named human "
                    "approver and a green eval gate before merge.",
                    "",
                ]
            )
        )
        out.append(DraftFix(s.cause, branch, persona_path, pr_path))
    return out


def write_review(review: Review, root: Path) -> Path:
    path = root / "docs/weekly-review" / f"{review.week_start.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_review(review))
    return path
