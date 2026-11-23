"""Phase 2 journeys: interfaces only (3.2). Each entry point raises NotBuiltYetError with its ticket."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.contracts.generated.booking_event import BookingEvent
from app.core.errors import NotBuiltYetError


class InboundSupport(Protocol):
    """J4: inbound support calls."""

    def answer(self, caller_e164: str) -> None: ...


class SupplyHunter(Protocol):
    """J5: B2B outreach to Tier-2/3 hotels and homestays, from CSV or Clay import only. No scraping."""

    def import_leads(self, csv_path: Path) -> int: ...


class ContactIntelligence(Protocol):
    """J6: analytics over contact reasons."""

    def weekly_drivers(self) -> list[str]: ...


class PromotionalOffers(Protocol):
    """J7: connected-trip offers. Requires a 140-series CLI, DCA-recorded promotional consent and
    a passed dark-pattern audit before any call."""

    def offer(self, event: BookingEvent) -> None: ...


def start_inbound_support(caller_e164: str) -> None:
    raise NotBuiltYetError("AV-J4")


def import_supply_leads(csv_path: Path) -> int:
    raise NotBuiltYetError("AV-J5")


def contact_drivers() -> list[str]:
    raise NotBuiltYetError("AV-J6")


def offer_connected_trip(event: BookingEvent) -> None:
    raise NotBuiltYetError("AV-J7")
