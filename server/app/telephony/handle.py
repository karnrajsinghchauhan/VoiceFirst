"""CallHandle: what a placed call is known by. Separate from dial so readers need not import dial."""

from __future__ import annotations

from dataclasses import dataclass

from app.compliance.clearance import GateClearance


@dataclass(frozen=True)
class CallHandle:
    call_id: str
    provider_call_id: str
    clearance: GateClearance
