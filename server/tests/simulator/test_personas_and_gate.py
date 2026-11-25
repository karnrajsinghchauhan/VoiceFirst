import json
from pathlib import Path

import pytest

from app.simulator.caller import load_personas
from app.simulator.evaluate import gate, run_one, run_suite, scorecard, targets
from tests.voice.helpers import settings

PERSONAS = load_personas()


def test_thirty_personas_c01_to_c30() -> None:
    assert [p.id for p in PERSONAS] == [f"C-{i:02d}" for i in range(1, 31)]


@pytest.mark.parametrize("persona", PERSONAS, ids=lambda p: p.id)
def test_persona_passes_text_mode(persona) -> None:  # type: ignore[no-untyped-def]
    for language in persona.languages:
        record = run_one(settings(), persona, language, 0, "text")
        assert record.task_passed, (language, record.failed_checks)


def test_runs_are_replayable() -> None:
    a = run_one(settings(), PERSONAS[0], "hinglish", 7, "text")
    b = run_one(settings(), PERSONAS[0], "hinglish", 7, "text")
    assert a.transcript == b.transcript and a.replay_key == b.replay_key


def test_audio_mode_runs_on_two_profiles() -> None:
    records = run_suite(settings(), [PERSONAS[0]], 1, "audio")
    assert {r.profile for r in records} >= {"clean", "mobile_3g"}
    assert all(r.audio for r in records)


def test_scorecard_meets_targets_in_text_mode() -> None:
    card = scorecard(run_suite(settings(), PERSONAS, 1, "text"), PERSONAS)
    assert targets(card) == []


def test_gate_flags_critical_drop_and_overall_drop() -> None:
    baseline = {"guardrail_rate": 0.99, "critical": {"C-06": 1.0}, "per_persona": {}}
    card = {"guardrail_rate": 0.97, "critical": {"C-06": 0.9}, "per_persona": {}}
    failures = gate(card, baseline)
    assert any("C-06" in f for f in failures) and any("1 point" in f for f in failures)
    assert gate(baseline | {"per_persona": {}}, baseline) == []


def test_baseline_file_is_present_for_both_modes() -> None:
    baseline = json.loads(
        (Path(__file__).resolve().parents[3] / "evals" / "baseline.json").read_text()
    )
    assert {"text", "audio"} <= set(baseline)
