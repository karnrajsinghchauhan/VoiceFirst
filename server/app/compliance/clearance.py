"""GateClearance: proof that a call passed every gate (9.1).

Two independent locks make it unforgeable:
1. Construction requires `_MINT`, a module-private object that only
   compliance.evaluate passes. Anything else raises ClearanceForgeryError.
2. telephony.dial consumes the clearance with a conditional UPDATE on the
   `clearances` row that evaluate() wrote. An object built by bypassing
   __init__ has no matching unconsumed, unexpired row, so dial refuses it.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from datetime import datetime

from app.compliance.context import CallPurpose
from app.core.errors import ClearanceForgeryError

_MINT = object()


@dataclass(frozen=True)
class GateClearance:
    clearance_id: str
    decision_id: str
    trace_id: str
    booking_event_id: str
    booking_id: str
    phone_e164: str
    cli_e164: str
    purpose: CallPurpose
    issued_at: datetime
    expires_at: datetime
    # An InitVar, not a field: dataclasses.replace() cannot copy it, so a minted
    # clearance cannot be laundered into a modified one.
    _mint: InitVar[object] = None

    def __post_init__(self, _mint: object) -> None:
        if _mint is not _MINT:
            raise ClearanceForgeryError("GateClearance can only be minted by compliance.evaluate")


def mint(**fields: object) -> GateClearance:
    """Only compliance.evaluate calls this."""
    return GateClearance(_mint=_MINT, **fields)  # type: ignore[arg-type]
