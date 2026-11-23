import itertools
from dataclasses import replace

import pytest

from app.core.errors import PurposeFieldViolationError
from app.providers.base import LlmTurn, ToolCall
from app.providers.latency import LatencyModel, SimTimer
from app.providers.llm.mock import MockLlm
from app.simulator.scenario import make_event, run_text
from app.voice.context import PurposeContext
from app.voice.tools import RecordingToolBackend
from tests.voice.helpers import agent_texts, persona, run, scripted, settings, tools


def test_cooperative_j1_sends_link_and_reads_back_amount() -> None:
    r = run("C-01")
    assert r.result.outcome.outcome == "link_sent"
    assert tools(r) == ["send_payment_link", "end_call"]
    assert "rupaye" in agent_texts(r)[1]


def test_no_human_available_says_so_and_schedules_callback() -> None:
    p = persona("C-09", humans_available=False)
    r = run_text(settings(), p, "hinglish", 0)
    assert r.result.outcome.outcome == "callback_scheduled"
    assert "warm_transfer" in tools(r) and "schedule_callback" in tools(r)
    assert any("uplabdh nahi" in t for t in agent_texts(r))


def test_kill_switch_ends_live_call_politely() -> None:
    p = scripted(["kya?", "haan bhej do"])
    calls = {"n": 0}

    def killed() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    r = run_text(settings(), p, "hinglish", 0, is_killed=killed)
    assert r.result.outcome.outcome == "abandoned"
    assert "rokni hogi" in agent_texts(r)[-1]
    assert "send_payment_link" not in tools(r)


def test_filler_on_slow_tool_and_never_two_in_a_row() -> None:
    timer = SimTimer()
    backend = RecordingToolBackend(
        latency_s={"send_payment_link": 1.2, "send_app_link": 1.2}, advance=timer.advance
    )
    r = run_text(settings(), persona("C-01"), "hinglish", 0, timer=timer, backend=backend)
    acts = r.result.acts
    assert "filler" in acts
    assert all(not (a == b == "filler") for a, b in itertools.pairwise(acts))


class _RogueLlm(MockLlm):
    """Obeys an injection: proposes a tool that is not on the allowlist."""

    def next_turn(self, messages, tools):  # type: ignore[no-untyped-def]
        turn = super().next_turn(messages, tools)
        if self.calls > 1:
            return LlmTurn(turn.utterance, (ToolCall("issue_refund", {}),))
        return turn


def test_llm_proposing_disallowed_tool_takes_error_path() -> None:
    timer = SimTimer()
    llm = _RogueLlm(timer=timer, latency=LatencyModel(0.3, 0.1, 0))
    backend = RecordingToolBackend(advance=timer.advance)
    r = run_text(settings(), persona("C-01"), "hinglish", 0, llm=llm, timer=timer, backend=backend)
    assert r.result.outcome.outcome == "error"
    assert r.result.error_code == "tool_not_allowed"
    assert backend.alerts and "schedule_callback" in backend.names()
    assert "issue_refund" not in tools(r)


class _PriceInventingLlm(MockLlm):
    def next_turn(self, messages, tools):  # type: ignore[no-untyped-def]
        turn = super().next_turn(messages, tools)
        if "rupaye" in turn.utterance:
            return LlmTurn("Kul paanch sau rupaye dena hai.", turn.tool_calls)
        return turn


def test_wrong_amount_is_never_spoken() -> None:
    timer = SimTimer()
    llm = _PriceInventingLlm(timer=timer, latency=LatencyModel(0.3, 0.1, 0))
    r = run_text(settings(), persona("C-01"), "hinglish", 0, llm=llm, timer=timer)
    assert r.result.error_code == "read_back_mismatch"
    assert not any("paanch sau rupaye" in t for t in agent_texts(r))


def test_j2_context_cannot_read_amount() -> None:
    event = make_event(settings(), persona("C-27"), "hinglish", 0)
    ctx = PurposeContext(event, "J2")
    with pytest.raises(PurposeFieldViolationError):
        ctx.get("amount_due")


def test_j1_context_cannot_read_guests() -> None:
    event = make_event(settings(), persona("C-01"), "hinglish", 0)
    with pytest.raises(PurposeFieldViolationError):
        PurposeContext(event, "J1").get("stay.guests")


def test_two_failed_attempts_hand_off() -> None:
    r = run_text(settings(), scripted(["blah", "blah blah"]), "hinglish", 0)
    assert r.result.outcome.outcome == "handed_off"
    assert r.result.handoff_summary is not None
    assert r.result.handoff_summary.reason == "repeated_failure"


def test_refused_link_is_never_asked_again() -> None:
    r = run_text(settings(), scripted(["nahi, abhi nahi"]), "hinglish", 0)
    assert r.result.outcome.outcome == "abandoned"
    assert "send_payment_link" not in tools(r)
    assert sum("payment link bhej doon" in t for t in agent_texts(r)) == 1


def test_anger_twice_hands_off() -> None:
    r = run_text(
        settings(), scripted(["Bakwaas! pagal ho kya!", "Bakwaas! Chor ho tum log!"]), "hinglish", 0
    )
    assert r.result.outcome.outcome == "handed_off"


def test_no_whatsapp_opt_in_never_sends_link() -> None:
    p = replace(scripted(["haan bhej do"]), whatsapp_opt_in=False)
    r = run_text(settings(), p, "hinglish", 0)
    assert "send_payment_link" not in tools(r)


def test_handoff_summary_is_at_most_five_lines_and_masked() -> None:
    r = run("C-06")
    assert r.result.outcome.handoff is not None
    assert len(r.result.outcome.handoff.summary.splitlines()) <= 5
    assert r.event.booking_id not in r.result.outcome.handoff.summary
    assert r.result.handoff_summary is not None
    assert r.result.handoff_summary.booking_masked.endswith(r.event.booking_id[-4:])
