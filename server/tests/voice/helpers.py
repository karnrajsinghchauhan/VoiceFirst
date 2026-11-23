"""Shared helpers for voice, simulator, chaos and compliance tests."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.core.config import Settings
from app.simulator.caller import PERSONA_DIR, Persona, load_persona
from app.simulator.scenario import Run, run_text


def settings() -> Settings:
    return Settings(environment="test", database_url="sqlite://")


def persona(pid: str, **overrides: Any) -> Persona:
    return replace(load_persona(PERSONA_DIR / f"{pid}.yaml"), **overrides)


def run(pid: str, language: str = "hinglish", seed: int = 0, **hooks: Any) -> Run:
    return run_text(settings(), persona(pid), language, seed, **hooks)  # type: ignore[arg-type]


def scripted(
    turns: list[Any], journey: str = "J1", language: str = "hinglish", **overrides: Any
) -> Persona:
    """An ad-hoc persona built on C-01 with a custom script."""
    base = persona("C-01")
    return replace(
        base,
        journey=journey,
        languages=(language,),
        turns={language: turns},
        on_act={},
        default={language: ""},
        disfluency_rate=0.0,
        **overrides,
    )


def agent_texts(r: Run) -> list[str]:
    return [t.text for t in r.result.transcript if t.speaker == "agent"]


def tools(r: Run) -> list[str]:
    return [t.name for t in r.result.outcome.tools_called]
