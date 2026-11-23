"""REQ-DPDP-01 (itemised notice), -02 (purpose tags), -04 (child on the line)."""

import pytest

from tests.voice.helpers import run


@pytest.mark.parametrize("language", ["hinglish", "en"])
def test_child_on_line_ends_without_discussing_booking(language: str) -> None:
    r = run("C-11", language)
    assert r.result.outcome.outcome == "minor_on_line"
    names = [t.name for t in r.result.outcome.tools_called]
    assert names == ["end_call"]
    after_opening = [t for t in r.result.transcript[1:] if t.speaker == "agent"]
    assert all(t.act in ("minor_ask_booker", "minor_end") for t in after_opening)
    assert not any("rupaye" in t.text or "rupees" in t.text for t in after_opening)
