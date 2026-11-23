"""S4 units: scorecard checks, storage, and the week-on-week drift alert."""

from __future__ import annotations

from app.costs.book import load_book
from app.incidents.service import list_open
from app.postcall.store import TranscriptTurn
from app.qa.drift import DriftThresholds, WeekMetrics, alert_drift, find_drift
from app.qa.scorecard import save_score, score_call, score_for
from app.simulator.caller import load_personas
from app.simulator.scenario import run_text
from tests.factories import make_settings


def _scored(persona_id: str):
    settings = make_settings()
    persona = next(p for p in load_personas() if p.id == persona_id)
    result = run_text(settings, persona, persona.languages[0], 0).result
    turns = [TranscriptTurn(t.speaker, t.text) for t in result.transcript]
    return result.outcome, score_call(result.outcome, turns, load_book(settings.costs_file))


def test_cooperative_call_passes_disclosure_guardrails_task():
    _, qa = _scored("C-01")
    checks = {c.name: c.passed for c in qa.checks}
    assert checks["disclosure"] and checks["guardrails"] and checks["task"] and checks["cost"]
    assert 0 <= qa.score <= 100


def test_card_reader_never_leaks_into_agent_text():
    _, qa = _scored("C-17")
    assert {c.name: c.passed for c in qa.checks}["guardrails"]


def test_score_is_stored_and_read_back(session, settings, clock):
    outcome, qa = _scored("C-01")
    assert score_for(session, outcome.call_id) is None
    save_score(session, settings.tenant_id, qa, clock.now())
    assert score_for(session, outcome.call_id) == qa.score


def test_drift_pages_on_each_threshold(session, settings, clock):
    prev = WeekMetrics(containment=0.55, csat=4.4, complaint_rate=0.001, p95_latency_ms=900)
    cur = WeekMetrics(containment=0.45, csat=3.9, complaint_rate=0.004, p95_latency_ms=1200)
    drifts = find_drift(prev, cur, DriftThresholds())
    assert {d.metric for d in drifts} == {"containment", "csat", "complaint_rate", "p95_latency_ms"}
    alert_drift(session, settings.tenant_id, clock.now(), drifts)
    assert sum("metric drift" in i.summary for i in list_open(session, settings.tenant_id)) == 4


def test_small_moves_do_not_page():
    prev = WeekMetrics(containment=0.55, csat=4.4, complaint_rate=0.001, p95_latency_ms=900)
    cur = WeekMetrics(containment=0.53, csat=4.3, complaint_rate=0.0015, p95_latency_ms=1000)
    assert find_drift(prev, cur, DriftThresholds()) == []
