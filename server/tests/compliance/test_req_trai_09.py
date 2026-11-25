"""REQ-TRAI-09: pilot dials +91 only. E.164 fuzzing."""

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.compliance.gates import gate_jurisdiction
from app.core.errors import JurisdictionNotEnabledError
from tests.compliance.helpers import make_ctx
from tests.factories import make_event, make_settings

SETTINGS = make_settings()
IN_MOBILE = re.compile(r"^\+91[6-9][0-9]{9}$")


def _ctx_for(phone: str):
    return make_ctx(SETTINGS, event=make_event(SETTINGS, customer={"phone_e164": phone}))


@given(st.from_regex(r"\A\+[1-9][0-9]{6,14}\Z"))
def test_any_e164(phone: str) -> None:
    ctx = _ctx_for(phone)
    if IN_MOBILE.match(phone):
        gate_jurisdiction(ctx)
    else:
        with pytest.raises(JurisdictionNotEnabledError):
            gate_jurisdiction(ctx)


@pytest.mark.parametrize(
    "phone",
    [
        "+14155550100",
        "+6591234567",
        "+66812345678",
        "+60123456789",
        "+447700900123",
        "+9198765432",
        "+915812345678",
        "+9198123456789",
    ],
)
def test_named_rejections(phone: str) -> None:
    with pytest.raises(JurisdictionNotEnabledError):
        gate_jurisdiction(_ctx_for(phone))


def test_disabled_country_code_rejects_india_too() -> None:
    settings = make_settings(compliance={"enabled_country_codes": []})
    with pytest.raises(JurisdictionNotEnabledError):
        gate_jurisdiction(make_ctx(settings))
