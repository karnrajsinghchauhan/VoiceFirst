"""Simulated time for the mock pipeline. Mock providers advance it by seeded latencies,
so latency metrics are reproducible and evals do not sleep."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class SimTimer:
    t: float = 0.0

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("time does not run backwards")
        self.t += seconds


@dataclass
class LatencyModel:
    """Lognormal-ish latency in seconds around a median, deterministic for a seed."""

    median_s: float
    spread: float
    seed: int
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def sample(self) -> float:
        return self.median_s * self._rng.lognormvariate(0.0, self.spread)
