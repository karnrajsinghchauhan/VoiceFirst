"""REQ-PAY-03: the read-back equals booking.amount_due in the same currency, in Indian numbering."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.simulator.scenario import make_event, run_text
from app.voice.normalise import amount_words
from tests.voice.helpers import persona, scripted
from tests.voice.helpers import settings as av_settings


@settings(max_examples=40, deadline=None)
@given(st.integers(min_value=0, max_value=200), st.sampled_from(["hinglish", "hi", "en"]))
def test_read_back_matches_amount_due(seed: int, language: str) -> None:
    yes = {"hinglish": "haan bhej do", "hi": "हाँ भेज दो", "en": "yes send it"}[language]
    p = scripted([yes], language=language)
    run = run_text(av_settings(), p, language, seed)  # type: ignore[arg-type]
    event = run.event
    expected = amount_words(event.amount_due.value, event.amount_due.currency, language)  # type: ignore[arg-type]
    link_turn = next(t for t in run.result.transcript if "j1_link_sent" in t.act)
    assert expected in link_turn.text
    assert not any(c.isdigit() for c in link_turn.text)


def test_amount_is_stated_once() -> None:
    run = run_text(av_settings(), persona("C-01"), "hinglish", 0)
    unit_mentions = sum(
        t.text.count("rupaye") for t in run.result.transcript if t.speaker == "agent"
    )
    assert unit_mentions == 1


def test_event_amounts_are_mostly_under_5000() -> None:
    p = persona("C-01")
    amounts = [
        float(make_event(av_settings(), p, "hinglish", s).amount_due.value) for s in range(200)
    ]
    assert sum(a < 5000 for a in amounts) / len(amounts) > 0.7
