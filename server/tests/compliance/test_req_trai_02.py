"""REQ-TRAI-02: series must match purpose. Property test across all pairs."""

from hypothesis import given
from hypothesis import strategies as st

from app.compliance.context import CATEGORY_BY_PURPOSE
from app.compliance.gates import gate_series
from app.core.errors import NumberSeriesMismatchError
from tests.compliance.helpers import make_ctx, service_cli

SERIES = ("140", "1600", "1601")
CLI_PURPOSES = ("service", "transactional", "promotional")
CALL_PURPOSES = ("J1", "J2", "J7")


def _expected_ok(series: str, cli_purpose: str, call: str) -> bool:
    promo_call = CATEGORY_BY_PURPOSE[call] == "promotional"  # type: ignore[index]
    series_ok = series == "140" if promo_call else series in ("1600", "1601")
    purpose_ok = (cli_purpose == "promotional") == promo_call
    return series_ok and purpose_ok


@given(st.sampled_from(SERIES), st.sampled_from(CLI_PURPOSES), st.sampled_from(CALL_PURPOSES))
def test_every_pair(series: str, cli_purpose: str, call: str) -> None:
    ctx = make_ctx(purpose=call, cli=service_cli(series=series, purpose=cli_purpose))
    if _expected_ok(series, cli_purpose, call):
        gate_series(ctx)
    else:
        try:
            gate_series(ctx)
        except NumberSeriesMismatchError:
            return
        raise AssertionError(f"{series}/{cli_purpose}/{call} should mismatch")


def test_exhaustive_matrix_has_both_outcomes() -> None:
    outcomes = {_expected_ok(s, p, c) for s in SERIES for p in CLI_PURPOSES for c in CALL_PURPOSES}
    assert outcomes == {True, False}
