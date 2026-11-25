"""REQ-TRAI-04: preference registry before every dial. Matrix of registry states."""

from dataclasses import replace
from datetime import timedelta

import pytest

from app.compliance.context import ConsentView
from app.compliance.gates import gate_dnd
from app.core.errors import PreferenceBlockedError
from tests.compliance.helpers import NOON_IST, make_ctx
from tests.factories import make_settings

STATES = ("none", "block_promo", "partial", "fully_blocked")
SIGNED = make_settings(compliance={"dnd_j1_transaction_signoff_ref": "COUNSEL-2026-001"})


def _explicit_only(purpose: str) -> tuple[ConsentView, ...]:
    return (
        ConsentView(
            basis="explicit",
            purpose=purpose,
            booking_id=None,
            obtained_at=NOON_IST - timedelta(days=1),
            expires_at=NOON_IST + timedelta(days=6),
            revoked_at=None,
        ),
    )


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("purpose", ["J1", "J2", "J7"])
@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("transaction_basis", [False, True])
def test_matrix(state: str, purpose: str, signed: bool, transaction_basis: bool) -> None:
    settings = SIGNED if signed else make_settings()
    ctx = make_ctx(settings, purpose=purpose, preference=state)
    if transaction_basis:
        ctx = replace(ctx, consents=(replace(ctx.consents[0], purpose=purpose),))
    else:
        ctx = replace(ctx, consents=_explicit_only(purpose))
    allowed = state == "none" or (purpose == "J1" and signed and transaction_basis)
    if allowed:
        gate_dnd(ctx)
    else:
        with pytest.raises(PreferenceBlockedError):
            gate_dnd(ctx)


def test_default_config_has_no_signoff() -> None:
    assert make_settings().compliance.dnd_j1_transaction_signoff_ref is None
