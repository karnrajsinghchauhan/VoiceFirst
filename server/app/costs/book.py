"""The cost book: unit prices loaded from config/costs.yaml, the single owner of every price.

Validated at the edge (the YAML file); everything downstream works in Decimal paise.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_CEILING, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from app.core.errors import ConfigError

ComponentName = Literal[
    "telephony",
    "a2p_termination",
    "stt",
    "llm",
    "tts",
    "orchestration_infra",
    "whatsapp",
    "storage_qa",
]
REQUIRED: tuple[ComponentName, ...] = (
    "telephony",
    "a2p_termination",
    "stt",
    "llm",
    "tts",
    "orchestration_infra",
    "whatsapp",
    "storage_qa",
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Component(_Model):
    name: ComponentName
    unit: str
    unit_price: Decimal
    units_per_minute: Decimal
    source: str
    source_url: str | None
    checked_at: date
    estimate: bool
    gst_applies: bool = False


class Comparison(_Model):
    vendor: str
    price: str
    currency: str
    unit: str
    source_url: str
    checked_at: date


class Assumptions(_Model):
    avg_call_minutes: Decimal
    resolution_rate: Decimal
    agent_tts_chars_per_minute: Decimal
    whatsapp_templates_per_call: Decimal


class CostBook(_Model):
    as_of: date
    currency: Literal["INR"]
    re_check_before_quoting: bool
    gst_rate: Decimal
    assumptions: Assumptions
    components: tuple[Component, ...]
    comparison: tuple[Comparison, ...]

    def component(self, name: ComponentName) -> Component:
        for c in self.components:
            if c.name == name:
                return c
        raise ConfigError(f"cost component {name} missing from the cost book")

    def unit_paise(self, name: ComponentName) -> Decimal:
        """Price of one unit in paise, GST included where it applies."""
        c = self.component(name)
        gst = (Decimal(1) + self.gst_rate) if c.gst_applies else Decimal(1)
        return c.unit_price * gst * 100

    def per_minute_paise(self, name: ComponentName) -> Decimal:
        return self.unit_paise(name) * self.component(name).units_per_minute

    def total_per_minute_paise(self) -> Decimal:
        return sum((self.per_minute_paise(c.name) for c in self.components), Decimal(0))

    def per_call_paise(self) -> Decimal:
        return self.total_per_minute_paise() * self.assumptions.avg_call_minutes

    def per_resolved_contact_paise(self) -> Decimal:
        return self.per_call_paise() / self.assumptions.resolution_rate

    def whatsapp_template_paise(self) -> int:
        """Billed per template in whole paise, rounded up (every template assumed paid)."""
        return int(self.unit_paise("whatsapp").to_integral_value(rounding=ROUND_CEILING))


@lru_cache(maxsize=8)
def load_book(path: str) -> CostBook:
    file = Path(path)
    if not file.is_file():
        raise ConfigError(f"cost book not found at {file}")
    book = CostBook.model_validate(yaml.safe_load(file.read_text()))
    missing = set(REQUIRED) - {c.name for c in book.components}
    if missing:
        raise ConfigError(f"cost book lacks components: {sorted(missing)}")
    for c in book.components:
        if not c.estimate and c.source_url is None:
            raise ConfigError(f"{c.name}: a non-estimate price needs a source_url")
    return book
