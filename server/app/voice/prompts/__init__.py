"""Versioned prompt files. PROMPT_VERSION names the directory; bump it and the CHANGELOG together."""

from __future__ import annotations

import re
import string
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from app.core.errors import PromptLintError
from app.core.types import Language
from app.voice.normalise import spoken_lang

PROMPT_VERSION = "v1"
_DIR = Path(__file__).parent / PROMPT_VERSION
_LANGS = ("hinglish", "hi", "en")

# Speaker-verb forms that mark the speaker's gender in Hindi (REQ-AI-02).
_MALE_SPEAKER = re.compile(
    r"\b(raha|sakta|bhejta|karta|deta|paaya) hoon\b|\bsamajh (gaya|paaya)\b|\bmain .* sakta\b"
    r"|रहा हूँ|सकता|भेजता|समझ गया|पाया"
)
_FEMALE_SPEAKER = re.compile(
    r"\b(rahi|sakti|bhejti|karti|deti|paayi) hoon\b|\bsamajh gayi\b|\bsakti\b"
    r"|रही हूँ|सकती|भेजती|समझ गई|पाई"
)


@lru_cache(maxsize=1)
def lines() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load((_DIR / "lines.yaml").read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PromptLintError("lines.yaml must be a mapping of act -> language -> text")
    for act, variants in raw.items():
        if not isinstance(variants, dict) or set(variants) != set(_LANGS):
            raise PromptLintError(f"act {act!r} must define exactly {_LANGS}")
    return raw


def system_prompt() -> str:
    return (_DIR / "system.md").read_text(encoding="utf-8")


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def render(act: str, language: Language, values: dict[str, str]) -> str:
    """Renders one line. A missing placeholder is a prompt bug, so it raises."""
    table = lines()
    if act not in table:
        raise PromptLintError(f"unknown act {act!r}")
    template = table[act][spoken_lang(language)]
    missing = placeholders(template) - set(values)
    if missing:
        raise PromptLintError(f"act {act!r} missing values {sorted(missing)}")
    return template.format(**values)


def lint_gender(gender: Literal["female", "male"]) -> None:
    """Every line must use speaker verbs matching the configured voice. Runs at boot."""
    wrong = _MALE_SPEAKER if gender == "female" else _FEMALE_SPEAKER
    for act, variants in lines().items():
        for lang, text in variants.items():
            if wrong.search(text):
                raise PromptLintError(
                    f"{act}/{lang} uses {'male' if gender == 'female' else 'female'} "
                    f"speaker verbs but the voice is {gender}"
                )
