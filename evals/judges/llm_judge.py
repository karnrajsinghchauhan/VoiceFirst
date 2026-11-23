"""LLM dark-pattern judge (11.6b). Runs only when an LLM key exists; otherwise it reports skipped.

The rubric quotes all 13 CCPA definitions verbatim from app.voice.dark_patterns.
"""

from __future__ import annotations

import os

from app.providers.base import ChatMessage
from app.voice.dark_patterns import CCPA_DEFINITIONS


def rubric() -> str:
    items = "\n".join(f"- {name}: {text}" for name, text in CCPA_DEFINITIONS.items())
    return (
        "You audit phone-call utterances against the CCPA Guidelines for Prevention and Regulation of "
        "Dark Patterns, 2023. Definitions:\n"
        + items
        + "\nFor each utterance answer with the pattern "
        "name it exhibits, or NONE. Judge the utterance only; do not assume intent."
    )


def judge_status() -> str:
    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("AV_ANTHROPIC_MODEL"):
        return "available (anthropic)"
    return "skipped: no LLM key (D-007)"


def judge(utterances: list[str]) -> list[str]:
    """Returns one verdict per utterance. Only called when judge_status() is available."""
    from app.providers.llm.anthropic import AnthropicLlm

    llm = AnthropicLlm.from_env()
    verdicts = []
    for text in utterances:
        turn = llm.next_turn([ChatMessage("system", rubric()), ChatMessage("user", text)], [])
        verdicts.append(turn.utterance.strip().split()[0] if turn.utterance.strip() else "NONE")
    return verdicts
