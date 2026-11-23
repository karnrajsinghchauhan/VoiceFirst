"""PII and payment-credential detection and redaction (REQ-PAY-01, P4).

Runs on STT output before it reaches the LLM or storage, and inside the logger.
Spoken digits arrive as words ("chaar paanch teen do", "four five three two"),
as Devanagari numerals, or as numerals, so detection works on runs of digit
tokens rather than on raw regexes alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Finding = Literal["pan", "otp", "long_number", "phone", "email", "upi_id", "cvv"]

_DIGIT_WORDS: dict[str, str] = {
    # English
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    # Hinglish (romanised Hindi)
    "shunya": "0",
    "sunya": "0",
    "ek": "1",
    "do": "2",
    "teen": "3",
    "tin": "3",
    "char": "4",
    "chaar": "4",
    "paanch": "5",
    "panch": "5",
    "paach": "5",
    "chhe": "6",
    "chhah": "6",
    "chah": "6",
    "che": "6",
    "chheh": "6",
    "saat": "7",
    "sat": "7",
    "aath": "8",
    "aat": "8",
    "nau": "9",
    "no": "9",
    # Devanagari
    "शून्य": "0",
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पांच": "5",
    "पाँच": "5",
    "छह": "6",
    "छः": "6",
    "छे": "6",
    "सात": "7",
    "आठ": "8",
    "नौ": "9",
}
_DEVANAGARI_NUMERALS = str.maketrans("०१२३४५६७८९", "0123456789")
_TOKEN = re.compile(r"[\wऀ-ॿ]+", re.UNICODE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_UPI = re.compile(r"\b[\w.-]{2,}@(?:ok)?[a-z]{2,}\b", re.IGNORECASE)
_OTP_CONTEXT = re.compile(r"\b(otp|o\s?t\s?p|code|pin|cvv|ओटीपी|पिन|कोड)\b", re.IGNORECASE)
_CVV_CONTEXT = re.compile(r"\b(cvv|cvc|पीछे\s+वाला|peeche\s+wala)\b", re.IGNORECASE)

# Digit words that are also common Hinglish words ("bhej do", "no"). Counted
# only inside a run that already has at least this many digits.
_MIN_RUN_DIGITS = 3


@dataclass(frozen=True)
class _Run:
    start: int
    end: int
    digits: str
    tokens: int


def luhn_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _token_digits(token: str) -> str | None:
    translated = token.translate(_DEVANAGARI_NUMERALS)
    if translated.isdigit():
        return translated
    return _DIGIT_WORDS.get(token.lower())


def _digit_runs(text: str) -> list[_Run]:
    runs: list[_Run] = []
    current: list[tuple[int, int, str]] = []
    for match in _TOKEN.finditer(text):
        digits = _token_digits(match.group(0))
        if digits is None:
            if current:
                runs.append(_close(current))
                current = []
            continue
        current.append((match.start(), match.end(), digits))
    if current:
        runs.append(_close(current))
    return [run for run in runs if len(run.digits) >= _MIN_RUN_DIGITS]


def _close(parts: list[tuple[int, int, str]]) -> _Run:
    return _Run(parts[0][0], parts[-1][1], "".join(part[2] for part in parts), len(parts))


def _classify(run: _Run, text: str) -> Finding | None:
    """None means an ordinary number (an amount, a year) that is left alone."""
    n = len(run.digits)
    if 12 <= n <= 19 and luhn_valid(run.digits):
        return "pan"
    if n == 10 and run.digits[0] in "6789":
        return "phone"
    if n >= 9:
        return "long_number"
    if _CVV_CONTEXT.search(text):
        return "cvv"
    # A code read out digit by digit is the shape of an OTP even without the word "OTP".
    if _OTP_CONTEXT.search(text) or run.tokens >= 4:
        return "otp"
    return None


def find_sensitive(text: str) -> set[Finding]:
    found: set[Finding] = set()
    for run in _digit_runs(text):
        finding = _classify(run, text)
        if finding is not None:
            found.add(finding)
    if _EMAIL.search(text):
        found.add("email")
    elif _UPI.search(text):
        found.add("upi_id")
    return found


PAYMENT_CREDENTIALS: frozenset[Finding] = frozenset({"pan", "otp", "cvv"})


def is_payment_credential(findings: set[Finding]) -> bool:
    return bool(findings & PAYMENT_CREDENTIALS)


def redact_text(text: str) -> str:
    """Replaces every digit run of 4+ digits, emails and UPI ids with a typed placeholder."""
    out = _EMAIL.sub("[REDACTED_EMAIL]", text)
    out = _UPI.sub("[REDACTED_UPI]", out)
    runs = _digit_runs(out)
    for run in reversed(runs):
        finding = _classify(run, out)
        if finding is not None:
            out = out[: run.start] + f"[REDACTED_{finding.upper()}]" + out[run.end :]
    return out
