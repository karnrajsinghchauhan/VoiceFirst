"""REQ-CP-01 / CP-02: no CCPA dark pattern in any prompt line, template or agent utterance;
the amount is stated once; no scarcity; a refused ask is never repeated."""

import pytest

from app.core.errors import DarkPatternError
from app.simulator.caller import load_personas
from app.simulator.scenario import run_text
from app.voice.dark_patterns import CCPA_DEFINITIONS, assert_clean, find_dark_patterns, find_nagging
from app.voice.prompts import lines, system_prompt
from tests.voice.helpers import settings as av_settings


def test_lexicon_covers_all_thirteen_patterns() -> None:
    assert len(CCPA_DEFINITIONS) == 13


def test_every_prompt_line_is_clean() -> None:
    for act, variants in lines().items():
        for lang, text in variants.items():
            assert find_dark_patterns(text) == [], f"{act}/{lang}"


def test_system_prompt_is_clean() -> None:
    assert find_dark_patterns(system_prompt()) == []


@pytest.mark.parametrize(
    "text",
    [
        "sirf 2 room bache hain, jaldi kijiye",
        "Only 3 rooms left!",
        "This offer expires in 10 minutes",
        "maine insurance bhi add kar diya",
        "aap pachtaenge",
        "convenience fee alag se lagegi",
        "special offer sirf aapke liye",
        "free trial ke baad har mahine charge",
        "yeh apk install kijiye",
        "pehle app download kijiye tabhi milega",
        "bas haan boliye",
    ],
)
def test_known_dark_patterns_are_caught(text: str) -> None:
    with pytest.raises(DarkPatternError):
        assert_clean(text)


@pytest.mark.parametrize("p", load_personas(), ids=lambda p: p.id)
def test_no_dark_pattern_in_any_utterance(p) -> None:  # type: ignore[no-untyped-def]
    for language in p.languages:
        for seed in range(2):
            r = run_text(av_settings(), p, language, seed)
            for t in r.result.transcript:
                if t.speaker == "agent":
                    assert find_dark_patterns(t.text) == [], t.text
            assert find_nagging(r.result.asks) == []
