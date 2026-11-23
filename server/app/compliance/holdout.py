"""J3 holdout. Decided before any gate and never overridden.

bucket = int(sha256(experiment_salt + booking_id).hexdigest(), 16) % 100; held out if bucket < percent.
"""

from __future__ import annotations

import hashlib


def bucket(experiment_salt: str, booking_id: str) -> int:
    return int(hashlib.sha256((experiment_salt + booking_id).encode()).hexdigest(), 16) % 100


def is_held_out(experiment_salt: str, booking_id: str, percent: int) -> bool:
    return bucket(experiment_salt, booking_id) < percent
