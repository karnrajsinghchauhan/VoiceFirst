from __future__ import annotations

import math
from statistics import NormalDist

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from app.analytics.lift import InsufficientSampleError, two_proportion_lift


def _reference(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float, float, float]:
    """Textbook formulation, written independently: (z, p, ci_low, ci_high)."""
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    z = (p1 - p2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    pval = 2 * (1 - NormalDist().cdf(abs(z)))
    half = 1.959963984540054 * math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return z, pval, (p1 - p2) - half, (p1 - p2) + half


def test_worked_example():
    r = two_proportion_lift(60, 100, 40, 100)
    assert r.lift == pytest.approx(0.2)
    assert r.z == pytest.approx(2.8284, abs=1e-4)
    assert r.p_value == pytest.approx(0.004678, abs=1e-5)
    assert (r.ci_low, r.ci_high) == pytest.approx((0.0642, 0.3358), abs=1e-4)
    assert r.significant


@given(
    n1=st.integers(1, 5000),
    n2=st.integers(1, 5000),
    f1=st.floats(0, 1),
    f2=st.floats(0, 1),
)
def test_matches_reference(n1, n2, f1, f2):
    x1, x2 = round(n1 * f1), round(n2 * f2)
    assume(0 < x1 + x2 < n1 + n2)
    r = two_proportion_lift(x1, n1, x2, n2)
    z, p, lo, hi = _reference(x1, n1, x2, n2)
    assert r.z == pytest.approx(z, rel=1e-9, abs=1e-9)
    assert r.p_value == pytest.approx(p, abs=1e-9)
    assert r.ci_low == pytest.approx(lo, abs=1e-9)
    assert r.ci_high == pytest.approx(hi, abs=1e-9)
    assert r.ci_low <= r.lift <= r.ci_high


@pytest.mark.parametrize(
    "args", [(0, 0, 1, 10), (1, 10, 0, 0), (11, 10, 1, 10), (0, 10, 0, 10), (10, 10, 10, 10)]
)
def test_undefined_inputs_raise(args):
    with pytest.raises(InsufficientSampleError):
        two_proportion_lift(*args)
