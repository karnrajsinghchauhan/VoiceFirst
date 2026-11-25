"""Builds GateContexts directly so each gate can be tested as the pure function it is."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

from app.compliance.context import CliView, ConsentView, GateContext
from app.core.config import Settings
from tests.factories import SERVICE_CLI, make_event, make_settings

NOON_IST = datetime(2026, 11, 23, 6, 30, tzinfo=UTC)


def transaction_consent(booking_id: str, purpose: str = "J1") -> ConsentView:
    return ConsentView(
        basis="transaction",
        purpose=purpose,
        booking_id=booking_id,
        obtained_at=NOON_IST - timedelta(days=3),
        expires_at=None,
        revoked_at=None,
    )


def service_cli(**overrides: Any) -> CliView:
    base = CliView(
        cli_e164=SERVICE_CLI,
        series="1600",
        purpose="transactional",
        oap="OAP-TEST",
        a2p_declared=True,
        declaration_ref="DLT-A2P-0001",
        dlt_recorded_at=datetime(2026, 10, 1, tzinfo=UTC),
        status="active",
    )
    return replace(base, **overrides)


def make_ctx(settings: Settings | None = None, **overrides: Any) -> GateContext:
    s = settings or make_settings()
    event = overrides.pop("event", None) or make_event(s)
    base = GateContext(
        event=event,
        purpose="J1",
        now=NOON_IST,
        kill_switch_engaged=False,
        campaigns_paused=False,
        consents=(transaction_consent(event.booking_id),),
        preference="none",
        opted_out_at=None,
        cli=service_cli(),
        attempts_for_event=0,
        last_dial_at_for_number=None,
        compliance=s.compliance,
        holdout=s.holdout,
    )
    return replace(base, **overrides)
