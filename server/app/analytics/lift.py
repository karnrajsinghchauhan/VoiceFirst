"""Lift against the J3 holdout: difference of two proportions with a two-sided z-test (M6).

The confidence interval uses the unpooled standard error (Wald interval for a
difference); the z-test uses the pooled standard error under H0: p_t == p_c.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

from app.core.errors import AgodaVoiceError


class InsufficientSampleError(AgodaVoiceError):
    """A group is empty or has no variance, so no interval or test is defined."""

    code = "insufficient_sample"


@dataclass(frozen=True)
class LiftResult:
    n_treated: int
    n_control: int
    treated_rate: float
    control_rate: float
    lift: float  # treated_rate - control_rate, absolute percentage points as a fraction
    ci_low: float
    ci_high: float
    confidence: float
    z: float
    p_value: float

    @property
    def significant(self) -> bool:
        return self.p_value < 1 - self.confidence


def two_proportion_lift(
    successes_treated: int,
    n_treated: int,
    successes_control: int,
    n_control: int,
    confidence: float = 0.95,
) -> LiftResult:
    if n_treated <= 0 or n_control <= 0:
        raise InsufficientSampleError("both groups need at least one booking")
    if not (0 <= successes_treated <= n_treated and 0 <= successes_control <= n_control):
        raise InsufficientSampleError("successes must lie between 0 and the group size")
    p_t = successes_treated / n_treated
    p_c = successes_control / n_control
    pooled = (successes_treated + successes_control) / (n_treated + n_control)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_treated + 1 / n_control))
    if se_pooled == 0:
        raise InsufficientSampleError("both groups have identical all-or-nothing outcomes")
    se_diff = math.sqrt(p_t * (1 - p_t) / n_treated + p_c * (1 - p_c) / n_control)
    z_crit = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    diff = p_t - p_c
    z = diff / se_pooled
    return LiftResult(
        n_treated=n_treated,
        n_control=n_control,
        treated_rate=p_t,
        control_rate=p_c,
        lift=diff,
        ci_low=diff - z_crit * se_diff,
        ci_high=diff + z_crit * se_diff,
        confidence=confidence,
        z=z,
        p_value=math.erfc(abs(z) / math.sqrt(2)),
    )
