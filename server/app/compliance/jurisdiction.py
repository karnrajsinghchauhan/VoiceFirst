"""JurisdictionPolicy (5.8). One implementation, IndiaPolicy; the pilot dials +91 only (REQ-TRAI-09)."""

from __future__ import annotations

import re
from typing import Protocol
from zoneinfo import ZoneInfo

from app.core.errors import JurisdictionNotEnabledError

_IN_MOBILE = re.compile(r"^\+91[6-9][0-9]{9}$")


class JurisdictionPolicy(Protocol):
    country_code: str
    timezone: ZoneInfo

    def validate_number(self, phone_e164: str) -> None: ...


class IndiaPolicy:
    country_code = "+91"
    timezone = ZoneInfo("Asia/Kolkata")

    def validate_number(self, phone_e164: str) -> None:
        if not _IN_MOBILE.match(phone_e164):
            raise JurisdictionNotEnabledError(
                f"not an enabled +91 mobile number: {phone_e164[:4]}***"
            )


def policy_for(phone_e164: str, enabled_country_codes: frozenset[str]) -> JurisdictionPolicy:
    if phone_e164.startswith("+91") and "+91" in enabled_country_codes:
        return IndiaPolicy()
    raise JurisdictionNotEnabledError(f"jurisdiction not enabled for {phone_e164[:3]}***")
