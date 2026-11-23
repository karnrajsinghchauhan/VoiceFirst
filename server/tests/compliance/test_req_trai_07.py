"""REQ-TRAI-07: 09:00-21:00 recipient local time (IST). Narrower allowed, wider rejected."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.compliance.gates import gate_window
from app.core.config import CallWindow
from app.core.errors import ConfigError, OutsideCallWindowError
from tests.compliance.helpers import make_ctx
from tests.factories import make_settings

IST = ZoneInfo("Asia/Kolkata")


def _at_ist(h: int, m: int, s: int) -> datetime:
    return datetime(2026, 11, 23, h, m, s, tzinfo=IST).astimezone(UTC)


@pytest.mark.parametrize(
    ("h", "m", "s", "ok"),
    [(8, 59, 59, False), (9, 0, 0, True), (20, 59, 59, True), (21, 0, 0, False), (23, 0, 0, False)],
)
def test_boundaries(h: int, m: int, s: int, ok: bool) -> None:
    ctx = make_ctx(now=_at_ist(h, m, s))
    if ok:
        gate_window(ctx)
    else:
        with pytest.raises(OutsideCallWindowError):
            gate_window(ctx)


@given(
    st.datetimes(
        min_value=datetime(2026, 1, 1), max_value=datetime(2027, 12, 31), timezones=st.just(UTC)
    )
)
def test_any_instant(at: datetime) -> None:
    local = at.astimezone(IST).time()
    ctx = make_ctx(now=at)
    if time(9) <= local < time(21):
        gate_window(ctx)
    else:
        with pytest.raises(OutsideCallWindowError):
            gate_window(ctx)


def test_narrower_window_is_honoured() -> None:
    settings = make_settings(compliance={"call_window": {"start": "10:00", "end": "19:00"}})
    with pytest.raises(OutsideCallWindowError):
        gate_window(make_ctx(settings, now=_at_ist(9, 30, 0)))
    gate_window(make_ctx(settings, now=_at_ist(10, 0, 0)))


@pytest.mark.parametrize(
    ("start", "end"), [(time(8, 59), time(21)), (time(9), time(21, 0, 1)), (time(12), time(11))]
)
def test_wider_or_inverted_window_is_rejected(start: time, end: time) -> None:
    with pytest.raises(ConfigError):
        CallWindow(start=start, end=end)


def test_utc_clock_does_not_leak_into_local_time() -> None:
    # 03:29:59 UTC is 08:59:59 IST.
    with pytest.raises(OutsideCallWindowError):
        gate_window(make_ctx(now=datetime(2026, 11, 23, 3, 29, 59, tzinfo=UTC)))
    gate_window(make_ctx(now=datetime(2026, 11, 23, 3, 29, 59, tzinfo=UTC) + timedelta(seconds=1)))
