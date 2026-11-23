"""A synthetic week of calls for the QA loop (S4 DONE). Real engine, scripted callers.

Most calls are ordinary personas; a share replays failure scripts found by probing the agent
(opt-out phrasing it misses, confusion it reads as refusal, a request for English, an amount
dispute, a slow payment-link tool). Outcomes and redacted transcripts are stored exactly as
post-call stores production calls, so the weekly review reads them the same way.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.core.bus import EventBus
from app.core.config import Settings
from app.core.db import transaction
from app.core.ids import phone_hash
from app.core.types import Language
from app.postcall.crypto import DataCipher
from app.postcall.store import TranscriptTurn, record_outcome, store_transcript
from app.providers.latency import SimTimer
from app.simulator.caller import Persona, load_personas
from app.simulator.scenario import Run, run_text
from app.voice.tools import RecordingToolBackend

ORDINARY = ("C-01", "C-03", "C-09", "C-10", "C-14", "C-17", "C-19", "C-20")

INJECTED: dict[str, tuple[str, list[list[str]]]] = {
    "opt_out_phrasing": ("C-01", [["pls mujhe aage se phone mat kijiyega"], ["haan"]]),
    "confusion": ("C-04", [["matlab? samajh nahi aaya"], ["matlab kya hai pay later?"]]),
    "english_request": (
        "C-01",
        [["sorry, can you speak in English please?"], ["English please, I don't understand Hindi"]],
    ),
    "amount_dispute": (
        "C-01",
        [
            ["kitne ka payment hai? amount galat lag raha hai"],
            ["nahi, yeh amount galat hai"],
            ["galat amount hai"],
        ],
    ),
}
SLOW_TOOL_LATENCY = {"send_payment_link": 1.4}


def _scripted(base: Persona, turns: list[list[str]]) -> Persona:
    lang: Language = "hinglish"
    return replace(
        base,
        id=f"{base.id}-inj",
        languages=(lang,),
        preferred_language=lang,
        turns={lang: turns},
        default={lang: turns[-1][0]},
    )


def _plan(personas: dict[str, Persona], i: int) -> tuple[Persona, Language, bool]:
    """Call i of a day: injected failures every 3rd call, slow tool every 7th."""
    slow = i % 7 == 6
    if i % 3 == 2:
        name = sorted(INJECTED)[(i // 3) % len(INJECTED)]
        base, turns = INJECTED[name]
        return _scripted(personas[base], turns), "hinglish", slow
    persona = personas[ORDINARY[i % len(ORDINARY)]]
    return persona, persona.languages[0], slow


def _run(settings: Settings, persona: Persona, language: Language, seed: int, slow: bool) -> Run:
    if not slow:
        return run_text(settings, persona, language, seed)
    timer = SimTimer()
    backend = RecordingToolBackend(latency_s=SLOW_TOOL_LATENCY, advance=timer.advance)
    return run_text(
        settings,
        persona,
        language,
        seed,
        timer=timer,
        backend=backend,
    )


def seed_week(
    session_factory: sessionmaker[Session],
    bus: EventBus,
    settings: Settings,
    cipher: DataCipher,
    week_start: date,
    calls_per_day: int,
) -> int:
    personas = {p.id: p for p in load_personas()}
    total = 0
    for day in range(7):
        for i in range(calls_per_day):
            persona, language, slow = _plan(personas, i)
            run = _run(settings, persona, language, day * 100 + i, slow)
            at = datetime.combine(week_start + timedelta(days=day), time(5, 0), UTC) + timedelta(
                minutes=i
            )
            call_id = f"syn-{week_start.isoformat()}-{day}-{i:03d}"
            outcome = run.result.outcome.model_copy(update={"call_id": call_id, "started_at": at})
            ph = phone_hash(run.event.customer.phone_e164, settings.phone_pepper)
            with transaction(session_factory) as s:
                record_outcome(s, bus, outcome, ph)
                store_transcript(
                    s,
                    cipher,
                    call_id=call_id,
                    phone_hash=ph,
                    at=at,
                    turns=[TranscriptTurn(t.speaker, t.text) for t in run.result.transcript],
                )
            total += 1
    return total
