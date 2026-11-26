"""Everything the gates need, loaded once per evaluation. Gates are pure functions of this."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.contracts.generated.booking_event import BookingEvent
from app.core.config import ComplianceSettings, HoldoutSettings

CallPurpose = Literal["J1", "J2", "J7"]
CallCategory = Literal["service", "transactional", "promotional"]
PreferenceState = Literal["none", "block_promo", "partial", "fully_blocked"]

# J1 rescues a payment on an existing transaction; J2 is a service call; J7 is the only promotional journey.
CATEGORY_BY_PURPOSE: dict[CallPurpose, CallCategory] = {
    "J1": "transactional",
    "J2": "service",
    "J7": "promotional",
}


@dataclass(frozen=True)
class ConsentView:
    basis: Literal["transaction", "explicit", "inquiry"]
    purpose: str
    booking_id: str | None
    obtained_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class CliView:
    cli_e164: str
    series: Literal["140", "1600", "1601"]
    purpose: CallCategory
    oap: str
    a2p_declared: bool
    declaration_ref: str | None
    dlt_recorded_at: datetime | None
    status: Literal["active", "paused", "retired"]


@dataclass(frozen=True)
class GateContext:
    event: BookingEvent
    purpose: CallPurpose
    now: datetime
    kill_switch_engaged: bool
    campaigns_paused: bool
    consents: tuple[ConsentView, ...]
    preference: PreferenceState
    opted_out_at: datetime | None
    cli: CliView | None
    attempts_for_event: int
    last_dial_at_for_number: datetime | None
    compliance: ComplianceSettings
    holdout: HoldoutSettings

    @property
    def category(self) -> CallCategory:
        return CATEGORY_BY_PURPOSE[self.purpose]
