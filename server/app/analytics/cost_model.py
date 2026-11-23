"""Unit prices for the cost model (7.8, REQ-WA-02). Every price is dated and tagged; re-check before quoting.

[V]  verified from a dated source in docs/sources.md.
[CD] carried from earlier research; confirm in discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

Tag = Literal["V", "CD"]


@dataclass(frozen=True)
class UnitPrice:
    name: str
    amount: Decimal
    currency: Literal["INR", "USD"]
    unit: str
    as_of: date
    tag: Tag
    source: str


SARVAM_STT = UnitPrice(
    "sarvam_stt",
    Decimal("0.49"),
    "INR",
    "per minute",
    date(2026, 11, 1),
    "V",
    "S-31 Sarvam pricing page",
)
SARVAM_BULBUL_V3 = UnitPrice(
    "sarvam_bulbul_v3",
    Decimal("3.00"),
    "INR",
    "per 1,000 characters",
    date(2026, 11, 1),
    "V",
    "S-31 Sarvam pricing page",
)
WHATSAPP_UTILITY_IN = UnitPrice(
    "whatsapp_utility_in",
    Decimal("0.1150"),
    "INR",
    "per template, before GST",
    date(2026, 10, 1),
    "V",
    "S-30 Meta",
)
WHATSAPP_MARKETING_IN = UnitPrice(
    "whatsapp_marketing_in",
    Decimal("0.8631"),
    "INR",
    "per template, before GST",
    date(2026, 10, 1),
    "V",
    "S-30 Meta",
)
GST = UnitPrice("gst", Decimal("0.18"), "INR", "rate", date(2026, 10, 1), "V", "S-30 Meta")
PLIVO_IN = UnitPrice(
    "plivo_in",
    Decimal("0.38"),
    "INR",
    "per minute, 30-s pulse",
    date(2026, 1, 1),
    "CD",
    "earlier research",
)
VAPI_HOSTING = UnitPrice(
    "vapi_hosting", Decimal("0.05"), "USD", "per minute", date(2026, 1, 1), "CD", "earlier research"
)
RETELL = UnitPrice(
    "retell_low",
    Decimal("0.07"),
    "USD",
    "per minute (range 0.07-0.31)",
    date(2026, 1, 1),
    "CD",
    "earlier research",
)
BLAND = UnitPrice(
    "bland_low",
    Decimal("0.12"),
    "USD",
    "per minute (range 0.12-0.14)",
    date(2026, 1, 1),
    "CD",
    "earlier research",
)
ELEVENLABS_AGENTS = UnitPrice(
    "elevenlabs_agents_overage",
    Decimal("0.08"),
    "USD",
    "per minute",
    date(2026, 1, 1),
    "CD",
    "earlier research",
)

ALL_PRICES: tuple[UnitPrice, ...] = (
    SARVAM_STT,
    SARVAM_BULBUL_V3,
    WHATSAPP_UTILITY_IN,
    WHATSAPP_MARKETING_IN,
    GST,
    PLIVO_IN,
    VAPI_HOSTING,
    RETELL,
    BLAND,
    ELEVENLABS_AGENTS,
)


def whatsapp_utility_paise() -> Decimal:
    """Every template is assumed paid, including in-window utility templates since 1 Oct 2026."""
    return WHATSAPP_UTILITY_IN.amount * (1 + GST.amount) * 100
