"""Shared literal types mirrored from contracts/schemas/common.json. tests/contract checks they match."""

from typing import Literal

Language = Literal["hi", "en", "hinglish", "unknown"]
Purpose = Literal["J1", "J2"]
