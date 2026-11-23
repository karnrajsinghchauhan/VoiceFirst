"""REQ-AI-01 (disclosure + provenance), REQ-AI-02 (voice gender lint), REQ-AI-03 (never claims human)."""

import re

import pytest

from app.core.errors import PromptLintError
from app.voice.prompts import lines, lint_gender

_CLAIMS_HUMAN = re.compile(r"main (ek )?insaan hoon|i am (a )?(human|real)|मैं इंसान हूँ", re.I)


def test_female_voice_lines_pass_gender_lint() -> None:
    lint_gender("female")


def test_male_voice_is_rejected_until_male_lines_exist() -> None:
    with pytest.raises(PromptLintError):
        lint_gender("male")


def test_brief_female_forms_present() -> None:
    assert "bol rahi hoon" in lines()["j1_opening"]["hinglish"]
    assert "bol raha hoon" not in " ".join(v for d in lines().values() for v in d.values())
