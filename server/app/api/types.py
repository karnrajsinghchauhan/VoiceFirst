"""Request field types that refuse JSON coercion: 0 is not false, 0 is not 1970-01-01."""

from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BeforeValidator, Field, StrictBool


def _iso_string(value: object) -> object:
    if not isinstance(value, str):
        raise ValueError("expected an ISO 8601 date-time string")
    return value


def _json_number(value: object) -> object:
    # JSON Schema "integer" admits 3.0, so integral floats pass; booleans and strings do not.
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("expected a JSON integer")
    return value


IsoDatetime = Annotated[AwareDatetime, BeforeValidator(_iso_string)]
JsonInt = Annotated[int, BeforeValidator(_json_number)]
# Constraints must precede the validator, or pydantic emits them as unknown schema keys.
DaysTtl = Annotated[int, Field(ge=1, le=730), BeforeValidator(_json_number)]

__all__ = ["DaysTtl", "IsoDatetime", "JsonInt", "StrictBool"]
