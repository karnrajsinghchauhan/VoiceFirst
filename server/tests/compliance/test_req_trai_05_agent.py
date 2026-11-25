"""REQ-TRAI-05 (agent side): opt-out phrases -> mark_dnc, confirm once, end the call.
The 90-day no-dial / no-re-request lock is tested in compliance (W-A)."""

import pytest

from app.simulator.scenario import run_text
from tests.voice.helpers import scripted
from tests.voice.helpers import settings as av_settings

PHRASES = [
    ("hinglish", "mujhe call mat karo"),
    ("hinglish", "band karo yeh sab"),
    ("hinglish", "dobara phone mat karna"),
    ("hinglish", "number hata do"),
    ("en", "Don't call me again"),
    ("en", "Please stop calling"),
    ("en", "do not call this number"),
    ("hi", "मुझे कॉल मत करो"),
    ("hi", "बंद करो"),
]


@pytest.mark.parametrize("language,phrase", PHRASES)
@pytest.mark.parametrize("position", [0, 1])
def test_opt_out_marks_dnc_confirms_once_and_ends(
    language: str, phrase: str, position: int
) -> None:
    turns = [phrase] if position == 0 else ["kaun?", phrase]
    p = scripted(turns, language=language)
    r = run_text(av_settings(), p, language, 0)  # type: ignore[arg-type]
    names = [t.name for t in r.result.outcome.tools_called]
    assert r.result.outcome.outcome == "opted_out"
    assert names[-2:] == ["mark_dnc", "end_call"]
    assert "send_payment_link" not in names
    agent = [t for t in r.result.transcript if t.speaker == "agent"]
    assert [t.act for t in agent].count("opt_out") == 1
    assert agent[-1].act == "opt_out"
    assert r.result.transcript[-1].speaker == "agent"
