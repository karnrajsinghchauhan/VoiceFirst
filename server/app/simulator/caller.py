"""Scripted, seeded synthetic caller (11.2, D-007).

A persona YAML gives the caller's script per language, replies keyed by the
agent's act, and the assertions its conversation must satisfy. A run is
replayable from (persona, language, seed, prompt_version, model_ids).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.core.errors import ConfigError
from app.core.types import Language
from app.voice.agent import Heard

PERSONA_DIR = Path(__file__).resolve().parents[3] / "evals" / "personas"
_DISFLUENCIES = ("umm", "uh", "matlab", "woh")


@dataclass(frozen=True)
class Expect:
    outcome: tuple[str, ...]
    tools_required: tuple[str, ...] = ()
    tools_forbidden: tuple[str, ...] = ()
    handoff: bool | None = None
    sensitive_data_spoken: bool | None = None
    must_say: tuple[str, ...] = ()


@dataclass(frozen=True)
class Persona:
    id: str
    title: str
    journey: str
    languages: tuple[Language, ...]
    preferred_language: Language
    flags: dict[str, bool]
    whatsapp_opt_in: bool
    humans_available: bool
    disfluency_rate: float
    interruption_propensity: float
    pause_profile: str
    turns: dict[str, list[Any]]
    on_act: dict[str, dict[str, Any]]
    default: dict[str, Any]
    expect: Expect
    guardrail_critical: bool
    cooperative: bool
    hidden_facts: tuple[str, ...]
    impairment_profiles: tuple[str, ...]


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(value) if isinstance(value, list) else (value,)


def load_persona(path: Path) -> Persona:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        exp = raw["expect"]
        return Persona(
            id=raw["id"],
            title=raw["title"],
            journey=raw["journey"],
            languages=tuple(raw["languages"]),
            preferred_language=raw.get("preferred_language", raw["languages"][0]),
            flags={"vip": False, "minor_suspected": False, **raw.get("flags", {})},
            whatsapp_opt_in=raw.get("whatsapp_opt_in", True),
            humans_available=raw.get("humans_available", True),
            disfluency_rate=float(raw.get("disfluency_rate", 0.0)),
            interruption_propensity=float(raw.get("interruption_propensity", 0.0)),
            pause_profile=raw.get("pause_profile", "normal"),
            turns=raw["turns"],
            on_act=raw.get("on_act", {}),
            default=raw.get("default", {}),
            expect=Expect(
                outcome=_as_tuple(exp["outcome"]),
                tools_required=_as_tuple(exp.get("tools_required")),
                tools_forbidden=_as_tuple(exp.get("tools_forbidden")),
                handoff=exp.get("handoff"),
                sensitive_data_spoken=exp.get("sensitive_data_spoken"),
                must_say=_as_tuple(exp.get("must_say")),
            ),
            guardrail_critical=bool(raw.get("guardrail_critical", False)),
            cooperative=bool(raw.get("cooperative", False)),
            hidden_facts=_as_tuple(raw.get("hidden_facts")),
            impairment_profiles=_as_tuple(raw.get("impairment_profiles", ["clean", "mobile_3g"])),
        )
    except KeyError as exc:
        raise ConfigError(f"persona {path.name} is missing {exc}") from exc


def load_personas(directory: Path = PERSONA_DIR) -> list[Persona]:
    return [load_persona(p) for p in sorted(directory.glob("C-*.yaml"))]


@dataclass
class ScriptedCaller:
    """Implements voice.agent.Listener for text mode."""

    persona: Persona
    language: Language
    seed: int
    _rng: random.Random = field(init=False)
    _index: int = field(init=False, default=0)
    _act_counts: dict[str, int] = field(init=False, default_factory=dict)
    heard_acts: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self._rng = random.Random(f"{self.persona.id}:{self.language}:{self.seed}")
        if self.language not in self.persona.turns:
            raise ConfigError(f"{self.persona.id} has no script for {self.language}")

    def _pick(self, entry: Any) -> Heard:
        if isinstance(entry, list):
            entry = self._rng.choice(entry)
        if isinstance(entry, dict):
            text, overlap = str(entry.get("text", "")), bool(entry.get("overlap", False))
        else:
            text, overlap = str(entry), False
        if text and self._rng.random() < self.persona.disfluency_rate:
            text = f"{self._rng.choice(_DISFLUENCIES)}, {text}"
        return Heard(text=text, overlap=overlap)

    def listen(self, act: str, agent_text: str) -> Heard:
        self.heard_acts.append(act)
        replies = self.persona.on_act.get(self.language, {})
        for part in act.split("+"):
            if part in replies:
                reply = replies[part]
                if isinstance(reply, list):
                    # A list under on_act is a sequence: one entry per time the act is heard.
                    n = self._act_counts.get(part, 0)
                    self._act_counts[part] = n + 1
                    reply = reply[min(n, len(reply) - 1)]
                return self._pick(reply)
        script = self.persona.turns[self.language]
        if self._index < len(script):
            entry = script[self._index]
            self._index += 1
            return self._pick(entry)
        return self._pick(self.persona.default.get(self.language, ""))
