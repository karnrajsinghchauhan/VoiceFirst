"""Builds a booking event and a call for one persona run, and runs it in text mode."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.contracts.generated.booking_event import BookingEvent
from app.core.clock import FrozenClock
from app.core.config import ClientSettings, Settings
from app.core.ids import sha256_hex
from app.core.types import Language, Purpose
from app.providers.latency import LatencyModel, SimTimer
from app.providers.llm.mock import MockLlm
from app.simulator.caller import Persona, ScriptedCaller
from app.voice.agent import CallSetup, ConversationResult, Listener, run_conversation
from app.voice.prompts import PROMPT_VERSION
from app.voice.tools import RecordingToolBackend

# Seed data per brief 2.5: Tier-2/3 and pilgrimage cities, most nightly amounts under INR 5,000.
_CITIES = (
    ("Varanasi", "Uttar Pradesh", "Ganga View Homestay"),
    ("Prayagraj", "Uttar Pradesh", "Sangam Residency"),
    ("Puri", "Odisha", "Jagannath Sea Inn"),
    ("Haridwar", "Uttarakhand", "Har Ki Pauri Guest House"),
    ("Shirdi", "Maharashtra", "Sai Kripa Lodge"),
    ("Udaipur", "Rajasthan", "Lake Pichola Haveli"),
)
_NAMES = ("Priya", "Rahul", "Sunita", "Amit", "Kavita", "Ramesh")
CALL_START = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)


_AREAS = ("Sector 62, Noida", "Andheri West", "Koramangala", "Gomti Nagar", "Vaishali Nagar")
# Slot starts in IST, as UTC: 10:00, 11:30, 14:30 and 17:00 on the day after CALL_START.
_SLOTS_UTC = (
    "2026-11-24T04:30:00Z",
    "2026-11-24T06:00:00Z",
    "2026-11-24T09:00:00Z",
    "2026-11-24T11:30:00Z",
)


def _as_appointment(payload: dict[str, Any], kind: str, rng: random.Random) -> dict[str, Any]:
    """A Cars24 booking: an appointment replaces the property and the stay (D-036)."""
    out = {k: v for k, v in payload.items() if k not in ("property", "stay")}
    out["status"] = "confirmed"
    out["purposes_allowed"] = ["J2"]
    out["appointment"] = {
        "kind": kind,
        "slot_start": rng.choice(_SLOTS_UTC),
        "area": rng.choice(_AREAS),
    }
    return out


def make_event(settings: Settings, persona: Persona, language: Language, seed: int) -> BookingEvent:
    rng = random.Random(f"event:{persona.id}:{language}:{seed}")
    city, state, prop = rng.choice(_CITIES)
    amount = rng.randrange(1800, 4999) if rng.random() < 0.85 else rng.randrange(5000, 14000)
    booking_id = "AGD" + sha256_hex(f"{persona.id}{language}{seed}")[:9].upper()
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tenant_id": settings.tenant_id,
        "trace_id": sha256_hex(f"trace{booking_id}")[:32],
        "event_id": f"evt_{booking_id}",
        "occurred_at": "2026-11-23T05:00:00Z",
        "booking_id": booking_id,
        "status": "payment_pending",
        "payment_option": "bnpl",
        "payment_due_at": "2026-11-25T18:29:59Z",
        "amount_due": {"value": f"{amount}.00", "currency": "INR"},
        "property": {"name": prop, "city": city, "state": state, "tier": 2},
        "stay": {
            "check_in": "2026-12-12",
            "check_out": "2026-12-14",
            "guests": rng.randint(1, 4),
        },
        "customer": {
            "first_name": rng.choice(_NAMES),
            "phone_e164": f"+9198{rng.randrange(10**7, 10**8)}",
            "preferred_language": persona.preferred_language,
            "whatsapp_opt_in": {"at": "2026-11-01T10:00:00Z", "source": "agoda_app_checkout"}
            if persona.whatsapp_opt_in
            else None,
        },
        "flags": persona.flags,
        "purposes_allowed": ["J1", "J2"],
    }
    if persona.appointment_kind is not None:
        payload = _as_appointment(payload, persona.appointment_kind, rng)
    return BookingEvent.model_validate(payload)


@dataclass
class Run:
    persona: Persona
    language: Language
    seed: int
    event: BookingEvent
    result: ConversationResult
    backend: RecordingToolBackend
    replay_key: str


def run_text(
    settings: Settings,
    persona: Persona,
    language: Language,
    seed: int,
    *,
    listener_factory: Callable[[ScriptedCaller, SimTimer], Listener] | None = None,
    llm: MockLlm | None = None,
    timer: SimTimer | None = None,
    backend: RecordingToolBackend | None = None,
    is_killed: Callable[[], bool] = lambda: False,
) -> Run:
    """Runs one persona conversation. Optional hooks let audio mode and chaos tests wrap pieces."""
    timer = timer or SimTimer()
    if persona.client is not None:
        settings = settings.model_copy(update={"client": ClientSettings(name=persona.client)})
    event = make_event(settings, persona, language, seed)
    llm = llm or MockLlm(timer=timer, latency=LatencyModel(0.35, 0.35, seed))
    backend = backend or RecordingToolBackend(
        humans_available=persona.humans_available, advance=timer.advance
    )
    caller = ScriptedCaller(persona, language, seed)
    listener: Listener = listener_factory(caller, timer) if listener_factory else caller
    purpose: Purpose = "J1" if persona.journey == "J1" else "J2"
    model_ids = {"llm": llm.model_id, "caller": "scripted-v1"}
    setup = CallSetup(
        event=event,
        purpose=purpose,
        call_id=f"call_{event.booking_id}",
        clearance_id=f"clr_{event.booking_id}",
        cli="+911600123456",
        settings=settings,
        clock=FrozenClock(CALL_START),
        llm=llm,
        backend=backend,
        listener=listener,
        is_killed=is_killed,
        monotonic=timer.now,
        model_ids=model_ids,
    )
    result = run_conversation(setup)
    replay = f"{persona.id}|{language}|{seed}|{PROMPT_VERSION}|{sorted(model_ids.items())}"
    return Run(persona, language, seed, event, result, backend, replay)
