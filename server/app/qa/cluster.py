"""Nightly clustering of failed and low-score calls by cause (S4).

Deterministic rules over the redacted transcript, tools and latency. The first rule that
matches names the cause; the order puts compliance-relevant causes first, because a
missed opt-out matters more than a slow tool on the same call.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from app.contracts.generated.call_outcome import CallOutcome
from app.postcall.store import TranscriptTurn
from app.qa.scorecard import LOW_SCORE, P95_TARGET_MS, QaScore

Cause = Literal[
    "missed_opt_out",
    "misheard_amount",
    "wrong_language",
    "customer_confusion",
    "slow_tool",
    "other",
]

# Opt-out wording, broader on purpose than the live guardrail: this net exists to find what
# the guardrail missed.
_OPT_OUT = re.compile(
    r"(phone|call|fon)\s*(mat|na)\s*(kar|kijiye|kijiyega|karna|karo|karein)|band\s*karo|"
    r"don'?t\s*call|stop\s*calling|do not call|remove my number|number hata|"
    r"फ़ोन मत|फोन मत|कॉल मत|मत कीजिए",
    re.IGNORECASE,
)
_AMOUNT_DISPUTE = re.compile(
    r"amount\s*(galat|wrong|sahi nahi)|wrong amount|galat amount|itna nahi|zyada (bol|bata)|"
    r"that'?s not the amount|रकम गलत|गलत अमाउंट",
    re.IGNORECASE,
)
_LANGUAGE_ASK = re.compile(
    r"(speak|talk|in)\s+english|english please|don'?t understand hindi|"
    r"hindi (mein|me) (bolo|baat)|हिंदी में बोलिए|अंग्रेज़ी",
    re.IGNORECASE,
)
_CONFUSION = re.compile(
    r"samajh nahi|matlab\??|kya matlab|what do you mean|confus|samjha nahi|समझ नहीं|मतलब",
    re.IGNORECASE,
)
_FILLER = re.compile(r"ek second ji|one moment|एक सेकंड", re.IGNORECASE)


@dataclass(frozen=True)
class Classified:
    call_id: str
    cause: Cause
    evidence: str


def _customer(turns: list[TranscriptTurn]) -> list[str]:
    return [t.text for t in turns if t.speaker == "customer"]


def _first(pattern: re.Pattern[str], texts: list[str]) -> str | None:
    return next((t for t in texts if pattern.search(t)), None)


def _missed_opt_out(o: CallOutcome, t: list[TranscriptTurn]) -> str | None:
    hit = _first(_OPT_OUT, _customer(t))
    return hit if hit and "mark_dnc" not in {x.name for x in o.tools_called} else None


def _misheard_amount(o: CallOutcome, t: list[TranscriptTurn]) -> str | None:
    return _first(_AMOUNT_DISPUTE, _customer(t))


def _wrong_language(o: CallOutcome, t: list[TranscriptTurn]) -> str | None:
    return _first(_LANGUAGE_ASK, _customer(t))


def _confusion(o: CallOutcome, t: list[TranscriptTurn]) -> str | None:
    hits = [c for c in _customer(t) if _CONFUSION.search(c)]
    return hits[0] if hits else None


def _slow_tool(o: CallOutcome, t: list[TranscriptTurn]) -> str | None:
    filler = _first(_FILLER, [x.text for x in t if x.speaker == "agent"])
    if o.latency_ms.p95 >= P95_TARGET_MS:
        return f"p95 {o.latency_ms.p95} ms" + (f"; filler: {filler}" if filler else "")
    return None


RULES: tuple[tuple[Cause, Callable[[CallOutcome, list[TranscriptTurn]], str | None]], ...] = (
    ("missed_opt_out", _missed_opt_out),
    ("misheard_amount", _misheard_amount),
    ("wrong_language", _wrong_language),
    ("customer_confusion", _confusion),
    ("slow_tool", _slow_tool),
)


def needs_review(outcome: CallOutcome, qa: QaScore) -> bool:
    return (
        qa.score < LOW_SCORE
        or outcome.outcome in ("error", "abandoned", "declined")
        or (outcome.handoff is not None and outcome.handoff.reason == "repeated_failure")
    )


def classify(outcome: CallOutcome, turns: list[TranscriptTurn]) -> Classified:
    for cause, rule in RULES:
        evidence = rule(outcome, turns)
        if evidence is not None:
            return Classified(outcome.call_id, cause, evidence)
    return Classified(outcome.call_id, "other", outcome.outcome)
