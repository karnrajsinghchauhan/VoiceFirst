"""Implements app.api.ports.Simulator over the eval scenario runner (mock providers, scripted caller)."""

from __future__ import annotations

from app.api.ports import SimulationResult, TranscriptLine
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.types import Language, Purpose
from app.simulator.assertions import check_run, guardrail_pass
from app.simulator.caller import Persona, load_personas
from app.simulator.scenario import run_text


class ScenarioSimulator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._personas: dict[str, Persona] = {p.id: p for p in load_personas()}

    def simulate(
        self, persona: str, seed: int, purpose: Purpose, language: Language
    ) -> SimulationResult:
        found = self._personas.get(persona)
        if found is None:
            raise NotFoundError(f"no persona {persona}")
        # A persona carries its own journey; the request's purpose must agree with it.
        if found.journey != purpose:
            raise NotFoundError(f"persona {persona} is a {found.journey} persona, not {purpose}")
        run = run_text(self._settings, found, language, seed)
        out = run.result.outcome
        return SimulationResult(
            persona=persona,
            seed=seed,
            purpose=purpose,
            outcome=out.outcome,
            tools_called=[t.name for t in out.tools_called],
            transcript=[
                TranscriptLine(speaker=t.speaker, text=t.text) for t in run.result.transcript
            ],
            assertions_passed=guardrail_pass(check_run(run)),
            trace_id=out.trace_id,
        )
