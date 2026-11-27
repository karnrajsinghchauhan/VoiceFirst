"""Deterministic demo and test data: bookings in Tier-2/3 and pilgrimage cities (2.5).

Most nightly amounts are under INR 5,000 (brief 2.5; the Travel Outlook share behind it is
unverified, see docs/sources.md). Everything is derived from a
seeded Random, so the same seed always yields the same bookings.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.compliance.consent import record_consent
from app.compliance.models import CliRow, PreferenceRow
from app.contracts.generated.booking_event import BookingEvent
from app.core.config import Settings
from app.core.ids import phone_hash

# (city, state, tier, property names)
_CITIES: tuple[tuple[str, str, int, tuple[str, ...]], ...] = (
    ("Varanasi", "Uttar Pradesh", 2, ("Ganga View Homestay", "Assi Ghat Residency")),
    ("Prayagraj", "Uttar Pradesh", 2, ("Sangam Stay", "Triveni Guest House")),
    ("Puri", "Odisha", 3, ("Jagannath Sea View Inn", "Swargadwar Lodge")),
    ("Haridwar", "Uttarakhand", 3, ("Har Ki Pauri Retreat", "Ganga Aarti Homestay")),
    ("Shirdi", "Maharashtra", 3, ("Sai Kripa Residency", "Shirdi Pilgrim Inn")),
    ("Udaipur", "Rajasthan", 2, ("Lake Pichola Haveli", "Fateh Sagar Stay")),
)
_NAMES = (
    "Priya",
    "Rahul",
    "Anita",
    "Suresh",
    "Kavita",
    "Amit",
    "Pooja",
    "Ramesh",
    "Sunita",
    "Vikram",
    "Meena",
    "Arjun",
    "Lakshmi",
    "Deepak",
    "Geeta",
    "Manoj",
)
_LANGUAGES = ("hinglish", "hinglish", "hinglish", "hi", "hi", "en", "unknown")
_STATUSES = ("payment_pending", "payment_pending", "payment_failed", "confirmed", "cancelled")


@dataclass(frozen=True)
class SeedPlan:
    events: tuple[BookingEvent, ...]
    dnd_phones: frozenset[str]
    shared_phone: str


def _nightly_amount(rng: random.Random) -> Decimal:
    # About 85% of nights under INR 5,000.
    rupees = rng.randint(900, 4999) if rng.random() < 0.85 else rng.randint(5000, 12000)
    return Decimal(rupees)


def _phone(rng: random.Random) -> str:
    return f"+91{rng.choice('6789')}{rng.randint(0, 999_999_999):09d}"


def build_seed(settings: Settings, *, count: int, seed: int, now: datetime) -> SeedPlan:
    rng = random.Random(seed)
    phones = [_phone(rng) for _ in range(count)]
    # Two bookings share one number so the cross-campaign cooldown is exercised.
    shared_phone = phones[0]
    if count > 1:
        phones[1] = shared_phone
    events: list[BookingEvent] = []
    for i in range(count):
        city, state, tier, names = rng.choice(_CITIES)
        status = rng.choice(_STATUSES)
        nights = rng.randint(1, 3)
        check_in = (now + timedelta(days=rng.randint(1, 20))).date()
        amount = _nightly_amount(rng) * nights
        payment_option = rng.choice(("pay_now", "bnpl", "bnpl", "zero_pay", "pay_at_hotel"))
        opted_in = rng.random() < 0.8
        events.append(
            BookingEvent.model_validate(
                _event_payload(
                    settings,
                    i=i,
                    now=now,
                    status=status,
                    payment_option=payment_option,
                    amount=amount,
                    city=city,
                    state=state,
                    tier=tier,
                    property_name=rng.choice(names),
                    check_in=check_in,
                    nights=nights,
                    guests=rng.randint(1, 4),
                    first_name=rng.choice(_NAMES),
                    phone=phones[i],
                    language=rng.choice(_LANGUAGES),
                    opted_in=opted_in,
                    vip=rng.random() < 0.02,
                )
            )
        )
    dnd = frozenset(rng.sample(phones[2:], k=min(20, max(0, count - 2))))
    return SeedPlan(events=tuple(events), dnd_phones=dnd, shared_phone=shared_phone)


def _event_payload(
    settings: Settings,
    *,
    i: int,
    now: datetime,
    status: str,
    payment_option: str,
    amount: Decimal,
    city: str,
    state: str,
    tier: int,
    property_name: str,
    check_in: date,
    nights: int,
    guests: int,
    first_name: str,
    phone: str,
    language: str,
    opted_in: bool,
    vip: bool,
) -> dict[str, Any]:
    occurred = now - timedelta(hours=3)
    return {
        "schema_version": "1.0.0",
        "tenant_id": settings.tenant_id,
        "trace_id": f"{i:032x}",
        "event_id": f"evt_seed_{i:05d}",
        "occurred_at": occurred.isoformat(),
        "booking_id": f"AGD{i:07d}",
        "status": status,
        "payment_option": payment_option,
        "payment_due_at": (now + timedelta(days=2)).isoformat(),
        "amount_due": {"value": f"{amount:.2f}", "currency": "INR"},
        "property": {"name": property_name, "city": city, "state": state, "tier": tier},
        "stay": {
            "check_in": check_in.isoformat(),
            "check_out": (check_in + timedelta(days=nights)).isoformat(),
            "guests": guests,
        },
        "customer": {
            "first_name": first_name,
            "phone_e164": phone,
            "preferred_language": language,
            "whatsapp_opt_in": {
                "at": (now - timedelta(days=5)).isoformat(),
                "source": "agoda_app_checkout",
            }
            if opted_in
            else None,
        },
        "flags": {"vip": vip, "minor_suspected": False},
        "purposes_allowed": ["J1", "J2"],
    }


def seed_registry(session: Session, settings: Settings, plan: SeedPlan) -> None:
    """CLI rows, a transaction-basis consent per booking and purpose, and DND numbers."""
    declared = datetime(2026, 10, 1, tzinfo=UTC)
    clis = settings.compliance.cli_by_purpose
    for cli, series, purpose in (
        (clis["J1"], "1600", "transactional"),
        (clis["J2"], "1601", "service"),
    ):
        session.merge(
            CliRow(
                cli_e164=cli,
                tenant_id=settings.tenant_id,
                series=series,
                purpose=purpose,
                oap="OAP-DEMO",
                a2p_declared=True,
                declaration_ref=f"DLT-A2P-{series}",
                dlt_recorded_at=declared,
                status="active",
                paused_reason=None,
            )
        )
    for event in plan.events:
        for purpose in ("J1", "J2"):
            record_consent(
                session,
                settings,
                phone_e164=event.customer.phone_e164,
                basis="transaction",
                purpose=purpose,
                channel="web",
                obtained_at=event.occurred_at,
                booking_id=event.booking_id,
                source_ref="booking",
                trace_id=event.trace_id,
            )
    for phone in plan.dnd_phones:
        session.merge(
            PreferenceRow(
                tenant_id=settings.tenant_id,
                phone_hash=phone_hash(phone, settings.phone_pepper),
                state="fully_blocked",
                synced_at=declared,
            )
        )
    session.flush()
