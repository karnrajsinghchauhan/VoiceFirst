"""Brief v3 S1: identity first. No city, property or amount before the person confirms who they are."""

from __future__ import annotations

import pytest

from app.simulator.assertions import check_run
from app.simulator.caller import load_personas
from app.simulator.scenario import run_text
from tests.factories import make_settings

PERSONAS = {p.id: p for p in load_personas()}
NOT_THE_BOOKER = ("C-11", "C-12", "C-13", "C-19")


def _runs(pid: str):
    persona = PERSONAS[pid]
    for language in persona.languages:
        for seed in range(3):
            yield run_text(make_settings(), persona, language, seed)


@pytest.mark.parametrize("pid", NOT_THE_BOOKER)
def test_non_booker_never_hears_a_booking_detail(pid: str) -> None:
    for run in _runs(pid):
        acts = [t.act for t in run.result.transcript if t.speaker == "agent"]
        assert not any("purpose" in a for a in acts), acts
        failed = [c for c in check_run(run) if c.name == "no_booking_detail_before_identity"]
        assert failed and failed[0].passed, failed[0].detail


@pytest.mark.parametrize("pid", sorted(PERSONAS))
def test_no_persona_hears_details_before_identity(pid: str) -> None:
    for run in _runs(pid):
        check = next(c for c in check_run(run) if c.name == "no_booking_detail_before_identity")
        assert check.passed, f"{pid} {run.language} {run.seed}: {check.detail}"


def test_opening_is_disclosure_then_identity_only() -> None:
    run = run_text(make_settings(), PERSONAS["C-01"], "hinglish", 0)
    first = run.result.transcript[0].text
    assert "AI assistant" in first and "record" in first
    assert f"{run.event.customer.first_name} ji se baat" in first
    for detail in (run.event.property.city, run.event.property.name, "payment", "booking"):
        assert detail not in first
