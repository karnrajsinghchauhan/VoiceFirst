"""Builders for test records. Defaults describe a dialable J1 booking in Varanasi."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.compliance.holdout import is_held_out
from app.compliance.models import CliRow, ConsentRow, OptOutRow, PreferenceRow
from app.contracts.generated.booking_event import BookingEvent
from app.core.config import Settings
from app.core.ids import new_id, new_trace_id, phone_hash

SERVICE_CLI = "+911600123456"
PROMO_CLI = "+91140123456"
PHONE = "+919812345678"


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {"environment": "test", "database_url": "sqlite://"}
    base.update(overrides)
    return Settings(**base)


def booking_id_with_holdout(settings: Settings, held_out: bool, start: int = 0) -> str:
    n = start
    while True:
        candidate = f"BK{n:08d}"
        if (
            is_held_out(settings.holdout.experiment_salt, candidate, settings.holdout.percent)
            == held_out
        ):
            return candidate
        n += 1


def make_event(settings: Settings, **overrides: Any) -> BookingEvent:
    booking_id = overrides.pop("booking_id", None) or booking_id_with_holdout(settings, False)
    customer = {
        "first_name": "Priya",
        "phone_e164": PHONE,
        "preferred_language": "hinglish",
        "whatsapp_opt_in": {"at": "2026-11-01T10:00:00Z", "source": "agoda_app_checkout"},
    }
    customer.update(overrides.pop("customer", {}))
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tenant_id": settings.tenant_id,
        "trace_id": new_trace_id(),
        "event_id": new_id("evt"),
        "occurred_at": "2026-11-23T05:00:00Z",
        "booking_id": booking_id,
        "status": "payment_pending",
        "payment_option": "bnpl",
        "payment_due_at": "2026-11-25T18:29:59Z",
        "amount_due": {"value": "4250.00", "currency": "INR"},
        "property": {
            "name": "Ganga View Homestay",
            "city": "Varanasi",
            "state": "Uttar Pradesh",
            "tier": 2,
        },
        "stay": {
            "check_in": str(date(2026, 12, 12)),
            "check_out": str(date(2026, 12, 14)),
            "guests": 2,
        },
        "customer": customer,
        "flags": {"vip": False, "minor_suspected": False},
        "purposes_allowed": ["J1", "J2"],
    }
    data.update(overrides)
    return BookingEvent.model_validate(data)


def seed_cli(session: Session, settings: Settings, **overrides: Any) -> CliRow:
    data: dict[str, Any] = {
        "cli_e164": SERVICE_CLI,
        "tenant_id": settings.tenant_id,
        "series": "1600",
        "purpose": "transactional",
        "oap": "OAP-TEST",
        "a2p_declared": True,
        "declaration_ref": "DLT-A2P-0001",
        "dlt_recorded_at": datetime(2026, 10, 1, tzinfo=UTC),
        "status": "active",
        "paused_reason": None,
    }
    data.update(overrides)
    row = CliRow(**data)
    session.merge(row)
    session.flush()
    return row


def seed_consent(
    session: Session, settings: Settings, event: BookingEvent, **overrides: Any
) -> ConsentRow:
    data: dict[str, Any] = {
        "consent_id": new_id("cns"),
        "tenant_id": settings.tenant_id,
        "phone_e164": event.customer.phone_e164,
        "basis": "transaction",
        "purpose": "J1",
        "channel": "web",
        "booking_id": event.booking_id,
        "obtained_at": datetime(2026, 11, 20, tzinfo=UTC),
        "expires_at": None,
        "revoked_at": None,
        "source_ref": "booking",
        "consent_manager_id": None,
        "artefact_ref": None,
        "evidence_uri": None,
        "trace_id": event.trace_id,
    }
    data.update(overrides)
    row = ConsentRow(**data)
    session.add(row)
    session.flush()
    return row


def seed_preference(session: Session, settings: Settings, phone: str, state: str) -> None:
    session.merge(
        PreferenceRow(
            phone_hash=phone_hash(phone, settings.phone_pepper),
            state=state,
            synced_at=datetime(2026, 11, 23, tzinfo=UTC),
        )
    )
    session.flush()


def seed_opt_out(session: Session, settings: Settings, phone: str, at: datetime) -> None:
    session.merge(
        OptOutRow(
            phone_hash=phone_hash(phone, settings.phone_pepper),
            opted_out_at=at,
            channel="voice",
            call_id=None,
        )
    )
    session.flush()


def days(n: float) -> timedelta:
    return timedelta(days=n)
