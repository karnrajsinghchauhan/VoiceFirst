"""REQ-PAY-01: card number, CVV, expiry, UPI PIN, OTP never reach the LLM or storage; the agent
interrupts and the call is marked sensitive_data_spoken. Luhn-valid PAN fuzzing in text and audio."""

from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.redaction import luhn_valid, redact_text
from app.providers import mock_codec
from app.providers.base import ChatMessage, LlmTurn, ToolSpec
from app.providers.latency import LatencyModel, SimTimer
from app.providers.llm.mock import MockLlm
from app.simulator.line import PROFILES, Line
from app.simulator.scenario import run_text
from app.voice.guardrails import classify
from tests.voice.helpers import scripted
from tests.voice.helpers import settings as av_settings

_DIGIT_WORDS = "shunya ek do teen chaar paanch chhah saat aath nau".split()


def _luhn_complete(prefix: list[int]) -> str:
    for check in range(10):
        candidate = "".join(map(str, prefix)) + str(check)
        if luhn_valid(candidate):
            return candidate
    raise AssertionError("unreachable")


pans = st.lists(st.integers(0, 9), min_size=15, max_size=15).map(
    lambda d: _luhn_complete([4, *d[1:]])
)
styles = st.sampled_from(["plain", "grouped", "words"])


def _spoken(pan: str, style: str) -> str:
    if style == "plain":
        return pan
    if style == "grouped":
        return " ".join(pan[i : i + 4] for i in range(0, len(pan), 4))
    return " ".join(_DIGIT_WORDS[int(c)] for c in pan)


class _SpyLlm(MockLlm):
    seen: list[str]

    def next_turn(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LlmTurn:
        self.seen.extend(m.content for m in messages)
        return super().next_turn(messages, tools)


@settings(max_examples=60, deadline=None)
@given(pans, styles)
def test_pan_in_text_never_reaches_llm_or_transcript(pan: str, style: str) -> None:
    utterance = f"mera card number {_spoken(pan, style)} hai"
    assert classify(utterance).payment_credential
    timer = SimTimer()
    llm = _SpyLlm(timer=timer, latency=LatencyModel(0.3, 0.1, 0))
    llm.seen = []
    persona = scripted([utterance, "theek hai, link bhej do"])
    run = run_text(av_settings(), persona, "hinglish", 0, llm=llm, timer=timer)
    assert run.result.outcome.sensitive_data_spoken
    assert run.result.outcome.redaction_applied
    stored = " ".join(t.text for t in run.result.transcript)
    assert pan not in stored and pan[-8:] not in "".join(stored.split())
    assert all(pan not in m and pan[-8:] not in "".join(m.split()) for m in llm.seen)
    warning = [t for t in run.result.transcript if "credential_warning" in t.act]
    assert warning, "agent must interrupt politely"


@settings(max_examples=30, deadline=None)
@given(pans, st.sampled_from(["clean", "loss_1", "mobile_3g"]), st.integers(0, 50))
def test_pan_through_audio_line_is_redacted(pan: str, profile: str, seed: int) -> None:
    utterance = f"card {_spoken(pan, 'grouped')}"
    received, _ = Line(PROFILES[profile], seed).transmit(mock_codec.encode(utterance))
    heard, _ = mock_codec.decode(received)
    redacted = redact_text(heard)
    digits = "".join(c for c in redacted if c.isdigit())
    # At most a short fragment survives the line plus redaction; never 9+ digits of the PAN.
    assert all(pan[i : i + 9] not in digits for i in range(len(pan) - 8))


def test_otp_and_cvv_trigger_the_warning() -> None:
    for text in ["OTP hai 4 8 2 9 1 5", "cvv 123", "chaar paanch aath do nau ek"]:
        assert classify(text).payment_credential, text


def test_agent_never_asks_for_card_details() -> None:
    from app.voice.prompts import lines

    asks = (
        "card number bataiye",
        "otp bataiye",
        "cvv bataiye",
        "tell me your card",
        "share the otp",
    )
    for variants in lines().values():
        for text in variants.values():
            assert not any(a in text.lower() for a in asks)


def test_persona_c17_never_repeats_card() -> None:
    from tests.voice.helpers import persona

    p = replace(persona("C-17"), disfluency_rate=0.0)
    run = run_text(av_settings(), p, "hinglish", 0)
    assert "4111" not in " ".join(t.text for t in run.result.transcript)
