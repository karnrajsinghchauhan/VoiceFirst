from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.errors import ReadBackMismatchError
from app.voice.normalise import amount_words, date_words, number_words, words_to_number

LANGS = ("hinglish", "hi", "en")


def test_brief_examples() -> None:
    assert amount_words("4250.00", "INR", "hinglish") == "chaar hazaar do sau pachaas rupaye"
    assert date_words(date(2026, 12, 12), "hinglish") == "baarah December"
    assert date_words(date(2026, 12, 12), "hi") == "बारह दिसंबर"


def test_indian_grouping() -> None:
    assert number_words(150000, "en") == "one lakh fifty thousand"
    assert number_words(12500000, "hinglish") == "ek crore pachchees lakh"
    assert amount_words("4250.50", "INR", "hi") == "चार हज़ार दो सौ पचास रुपये और पचास पैसे"


# Below 100 crore the crore count stays under 100, which is every real booking amount.
@given(st.integers(min_value=0, max_value=999_999_999), st.sampled_from(LANGS))
def test_round_trip(n: int, lang: str) -> None:
    assert words_to_number(number_words(n, lang), lang) == n  # type: ignore[arg-type]


@given(
    st.integers(min_value=0, max_value=9_999_999),
    st.integers(min_value=0, max_value=99),
    st.sampled_from(LANGS),
)
def test_amount_read_back_contains_whole_rupees(rupees: int, paise: int, lang: str) -> None:
    spoken = amount_words(f"{rupees}.{paise:02d}", "INR", lang)  # type: ignore[arg-type]
    assert spoken.startswith(number_words(rupees, lang))  # type: ignore[arg-type]
    assert not any(c.isdigit() for c in spoken)


def test_unknown_currency_raises() -> None:
    with pytest.raises(ReadBackMismatchError):
        amount_words("10.00", "USD", "en")


def test_unknown_reads_as_hinglish() -> None:
    assert number_words(42, "unknown") == number_words(42, "hinglish")
