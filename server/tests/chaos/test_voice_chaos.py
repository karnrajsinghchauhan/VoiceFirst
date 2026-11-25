"""11.11 voice chaos: kill or slow STT, TTS, LLM and the backend mid-call.

Expected every time: a typed error, an apology, a scheduled human callback, an
alert, and the same provider object throughout (never a switch).
"""

import pytest

from app.core.errors import ProviderError
from app.providers.latency import LatencyModel, SimTimer
from app.providers.llm.mock import MockLlm
from app.providers.stt.mock import MockStt
from app.providers.tts.mock import MockTts
from app.simulator.audio import AudioListener
from app.simulator.caller import ScriptedCaller
from app.simulator.line import PROFILES, Line
from app.simulator.scenario import Run, run_text
from app.voice.tools import RecordingToolBackend
from tests.voice.helpers import persona, settings


def _assert_error_path(run: Run, backend: RecordingToolBackend, code: str) -> None:
    assert run.result.outcome.outcome == "error"
    assert run.result.error_code == code
    assert backend.alerts and backend.alerts[0][0] == code
    assert "schedule_callback" in backend.names()
    agent = [t for t in run.result.transcript if t.speaker == "agent"]
    assert agent[-1].act == "error_apology"


def _audio_run(
    *, stt_fail: bool = False, tts_fail: bool = False
) -> tuple[Run, RecordingToolBackend]:
    timer = SimTimer()
    backend = RecordingToolBackend(advance=timer.advance)
    stt = MockStt(timer, LatencyModel(0.1, 0.1, 0))
    agent_tts = MockTts(timer, LatencyModel(0.1, 0.1, 1))

    def factory(caller: ScriptedCaller, t: SimTimer) -> AudioListener:
        return AudioListener(
            caller=caller,
            tts=MockTts(t, LatencyModel(0.1, 0.1, 2)),
            agent_tts=agent_tts,
            stt=stt,
            line=Line(PROFILES["clean"], 0),
            timer=t,
            language="hinglish",
            seed=0,
        )

    # The provider dies after the call is live: the opening has already been spoken.
    stt.fail = stt_fail
    agent_tts.fail = tts_fail
    run = run_text(
        settings(),
        persona("C-01"),
        "hinglish",
        0,
        listener_factory=factory,
        timer=timer,
        backend=backend,
    )
    return run, backend


@pytest.mark.parametrize("fail_after", [1, 2])
def test_llm_dies_mid_call(fail_after: int) -> None:
    timer = SimTimer()
    llm = MockLlm(timer=timer, latency=LatencyModel(0.3, 0.1, 0), fail_after_calls=fail_after)
    backend = RecordingToolBackend(advance=timer.advance)
    run = run_text(
        settings(), persona("C-04"), "hinglish", 0, llm=llm, timer=timer, backend=backend
    )
    _assert_error_path(run, backend, "provider_error")
    assert run.result.outcome.model_ids["llm"] == llm.model_id


def test_llm_slow_times_out() -> None:
    timer = SimTimer()
    llm = MockLlm(timer=timer, latency=LatencyModel(0.3, 0.1, 0), slow_s=5.0)
    backend = RecordingToolBackend(advance=timer.advance)
    run = run_text(
        settings(), persona("C-01"), "hinglish", 0, llm=llm, timer=timer, backend=backend
    )
    _assert_error_path(run, backend, "provider_timeout")


def test_stt_dies_mid_call() -> None:
    run, backend = _audio_run(stt_fail=True)
    _assert_error_path(run, backend, "provider_error")


def test_tts_dies_mid_call() -> None:
    run, backend = _audio_run(tts_fail=True)
    _assert_error_path(run, backend, "provider_error")


def test_whatsapp_send_fails_mid_call() -> None:
    timer = SimTimer()
    backend = RecordingToolBackend(
        advance=timer.advance, fail_tools=frozenset({"send_payment_link"})
    )
    run = run_text(settings(), persona("C-01"), "hinglish", 0, timer=timer, backend=backend)
    _assert_error_path(run, backend, "provider_error")
    assert "send_payment_link" not in [t.name for t in run.result.outcome.tools_called]


def test_callback_backend_also_down_raises_loudly() -> None:
    timer = SimTimer()
    llm = MockLlm(timer=timer, latency=LatencyModel(0.3, 0.1, 0), fail_after_calls=1)
    backend = RecordingToolBackend(
        advance=timer.advance, fail_tools=frozenset({"schedule_callback"})
    )
    with pytest.raises(ProviderError):
        run_text(settings(), persona("C-01"), "hinglish", 0, llm=llm, timer=timer, backend=backend)
    assert backend.alerts  # the alert went out before the second failure
