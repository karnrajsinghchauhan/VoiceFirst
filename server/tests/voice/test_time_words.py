"""Spoken appointment times (D-036): part of day, 12-hour clock, and the special half hours."""

from __future__ import annotations

from datetime import time

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.voice.normalise import number_words, time_words

SLOTS = st.builds(time, st.integers(9, 20), st.sampled_from([0, 30]))


@pytest.mark.parametrize(
    ("t", "hinglish", "en"),
    [
        (time(11, 0), "subah gyaarah baje", "eleven a.m."),
        (time(13, 30), "dopahar dedh baje", "one thirty p.m."),
        (time(14, 30), "dopahar dhaai baje", "two thirty p.m."),
        (time(17, 30), "shaam saadhe paanch baje", "five thirty p.m."),
        (time(20, 0), "raat aath baje", "eight p.m."),
    ],
)
def test_known_slots(t: time, hinglish: str, en: str) -> None:
    assert time_words(t, "hinglish") == hinglish
    assert time_words(t, "en") == en


@given(SLOTS)
def test_every_call_window_slot_names_its_hour(t: time) -> None:
    hour12 = t.hour % 12 or 12
    for lang in ("hinglish", "hi", "en"):
        spoken = time_words(t, lang)  # type: ignore[arg-type]
        assert not any(ch.isdigit() for ch in spoken)
        if not (t.minute and hour12 in (1, 2) and lang != "en"):
            assert number_words(hour12, lang) in spoken  # type: ignore[arg-type]


def test_odd_minutes_are_refused() -> None:
    with pytest.raises(ValueError):
        time_words(time(11, 15), "hinglish")
