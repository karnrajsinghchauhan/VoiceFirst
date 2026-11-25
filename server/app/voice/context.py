"""Purpose-limited context builder (REQ-DPDP-02).

The agent reads booking facts only through PurposeContext. A field is readable
for a purpose only if its x-purposes tag in contracts/schemas/booking_event.json
lists that purpose; any other read raises PurposeFieldViolationError.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.contracts.generated.booking_event import BookingEvent
from app.core.errors import PurposeFieldViolationError
from app.core.types import Purpose

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "contracts" / "schemas" / "booking_event.json"


def _walk(props: dict[str, Any], prefix: str) -> dict[str, frozenset[str]]:
    tags: dict[str, frozenset[str]] = {}
    for name, spec in props.items():
        path = f"{prefix}{name}"
        if "x-purposes" in spec:
            tags[path] = frozenset(spec["x-purposes"])
        elif "properties" in spec:
            tags.update(_walk(spec["properties"], f"{path}."))
        else:
            raise PurposeFieldViolationError(f"field {path} has no x-purposes tag")
    return tags


@lru_cache(maxsize=1)
def field_purposes() -> dict[str, frozenset[str]]:
    """Dotted field path -> purposes allowed to read it. Raises on any untagged leaf."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _walk(schema["properties"], "")


def _lookup(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        value = value[part]
    return value


class PurposeContext:
    """Read-only view of a booking event restricted to one purpose."""

    def __init__(self, event: BookingEvent, purpose: Purpose) -> None:
        if purpose not in event.purposes_allowed:
            raise PurposeFieldViolationError(f"booking does not allow purpose {purpose}")
        self.purpose = purpose
        data = event.model_dump(mode="json")
        self._values = {
            path: _lookup(data, path)
            for path, purposes in field_purposes().items()
            if purpose in purposes
        }

    def get(self, path: str) -> Any:
        if path not in self._values:
            raise PurposeFieldViolationError(f"{path} is not readable for {self.purpose}")
        return self._values[path]

    def has(self, path: str) -> bool:
        return path in self._values

    def as_dict(self) -> dict[str, Any]:
        return dict(self._values)
