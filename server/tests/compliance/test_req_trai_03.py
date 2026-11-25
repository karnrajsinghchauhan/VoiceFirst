"""REQ-TRAI-03: a recorded consent basis; explicit/inquiry consent lasts 7 days or until revoked."""

from dataclasses import replace
from datetime import timedelta

import pytest

from app.compliance.consent import expiry_for
from app.compliance.context import ConsentView
from app.compliance.gates import gate_consent
from app.core.errors import ConsentExpiredError, ConsentMissingError
from tests.compliance.helpers import NOON_IST, make_ctx
from tests.factories import make_settings


def _explicit(obtained_offset: timedelta) -> ConsentView:
    settings = make_settings()
    obtained = NOON_IST + obtained_offset
    return ConsentView(
        basis="explicit",
        purpose="J1",
        booking_id=None,
        obtained_at=obtained,
        expires_at=expiry_for(settings, "explicit", obtained),
        revoked_at=None,
    )


def test_expiry_minus_one_second_passes() -> None:
    consent = _explicit(-timedelta(days=7) + timedelta(seconds=1))
    gate_consent(make_ctx(consents=(consent,)))


def test_expiry_exact_fails() -> None:
    with pytest.raises(ConsentExpiredError):
        gate_consent(make_ctx(consents=(_explicit(-timedelta(days=7)),)))


def test_expiry_plus_one_second_fails() -> None:
    with pytest.raises(ConsentExpiredError):
        gate_consent(make_ctx(consents=(_explicit(-timedelta(days=7, seconds=1)),)))


def test_inquiry_lasts_seven_days() -> None:
    settings = make_settings()
    assert expiry_for(settings, "inquiry", NOON_IST) == NOON_IST + timedelta(days=7)


def test_renewal_extends_by_seven_days() -> None:
    old = _explicit(-timedelta(days=7, seconds=1))
    renewed = _explicit(-timedelta(seconds=1))
    gate_consent(make_ctx(consents=(old, renewed)))


def test_revoked_consent_fails() -> None:
    consent = replace(_explicit(-timedelta(days=1)), revoked_at=NOON_IST - timedelta(hours=1))
    with pytest.raises(ConsentExpiredError):
        gate_consent(make_ctx(consents=(consent,)))


def test_no_record_fails() -> None:
    with pytest.raises(ConsentMissingError):
        gate_consent(make_ctx(consents=()))


def test_other_purpose_does_not_count() -> None:
    consent = replace(_explicit(-timedelta(days=1)), purpose="J2")
    with pytest.raises(ConsentMissingError):
        gate_consent(make_ctx(consents=(consent,)))


def test_transaction_basis_is_bound_to_its_booking() -> None:
    ctx = make_ctx()
    wrong = replace(ctx.consents[0], booking_id="OTHER-BOOKING")
    with pytest.raises(ConsentExpiredError):
        gate_consent(replace(ctx, consents=(wrong,)))


def test_transaction_basis_ends_when_booking_cancelled() -> None:
    ctx = make_ctx()
    cancelled = ctx.event.model_copy(update={"status": "cancelled"})
    with pytest.raises(ConsentExpiredError):
        gate_consent(replace(ctx, event=cancelled))
