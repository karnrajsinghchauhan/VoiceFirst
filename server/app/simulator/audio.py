"""L5 audio-mode listener: caller text -> mock TTS -> line simulator -> mock STT -> agent.

Content errors come from the real signal path (codec + impairments). Timing
metrics (end-of-speech to first agent audio, barge-in stop, false cutoff,
false interruption) come from an explicit timing model of VAD, endpointing and
turn detection, stated here so the report can say what was simulated. It is a
model, not a measurement of a real VAD; M8 replaces it with real audio.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from app.core.types import Language
from app.providers import mock_codec
from app.providers.latency import SimTimer
from app.providers.stt.mock import MockStt
from app.providers.tts.mock import MockTts
from app.simulator.caller import ScriptedCaller
from app.simulator.line import Line, char_error_rate, word_error_rate
from app.voice.agent import Heard
from app.voice.guardrails import BACKCHANNEL_ONLY, classify
from app.voice.turn_config import MAX_ENDPOINTING_S, MIN_ENDPOINTING_S, MIN_INTERRUPTION_S

# Speech needed before an interruption is detected; same value the worker pins.
VAD_DETECT_S = MIN_INTERRUPTION_S
TTS_FLUSH_S = 0.04
WORDS_PER_S = {"normal": 2.6, "slow": 1.4, "long_initial_silence": 2.6}
_INCOMPLETE = re.compile(r"(\.\.\.|,|\b(aur|and|lekin|but|ki|to)\b)\s*$", re.IGNORECASE)


@dataclass
class TurnMetrics:
    reference: str
    hypothesis: str
    cer: float
    wer: float
    eos_to_first_audio_s: float
    false_cutoff: bool
    barge_in_stop_s: float | None
    false_interruption: bool
    line_delay_ms: float


def _phrases(text: str) -> list[str]:
    return [p for p in re.split(r"(?<=\.\.\.)|(?<=,)", text) if p.strip()]


@dataclass
class AudioListener:
    caller: ScriptedCaller
    tts: MockTts
    agent_tts: MockTts
    stt: MockStt
    line: Line
    timer: SimTimer
    language: Language
    seed: int
    metrics: list[TurnMetrics] = field(default_factory=list)
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(f"audio:{self.caller.persona.id}:{self.seed}")

    def _false_cutoff(self, text: str) -> bool:
        """The endpointer fires inside a pause the speaker had not finished."""
        profile = self.caller.persona.pause_profile
        if profile != "slow":
            return False
        for phrase in _phrases(text)[:-1]:
            pause = self._rng.uniform(0.9, 1.4)
            wait = MAX_ENDPOINTING_S if _INCOMPLETE.search(phrase) else MIN_ENDPOINTING_S
            if pause > wait:
                return True
        return False

    _pending: tuple[TurnMetrics, float, float, float] | None = field(init=False, default=None)

    def _speak_agent(self, agent_text: str) -> None:
        """The agent's line goes out through the agent TTS, then its latency is complete."""
        t0 = self.timer.now()
        self.agent_tts.synthesize(agent_text, self.language)
        tts_first = self.timer.now() - t0
        if self._pending is None:
            return
        metric, heard_at, endpoint_s, stt_s = self._pending
        # Preemptive generation (pinned in livekit_worker): STT final + LLM run while the
        # endpointer waits, so the slower of the two gates the reply, then TTS first audio.
        agent_work = stt_s + (t0 - heard_at)
        metric.eos_to_first_audio_s = max(endpoint_s, agent_work) + tts_first
        self._pending = None

    def finish(self, last_agent_text: str) -> None:
        self._speak_agent(last_agent_text)

    def listen(self, act: str, agent_text: str) -> Heard:
        self._speak_agent(agent_text)
        heard = self.caller.listen(act, agent_text)
        audio = mock_codec.from_pcm16(self.tts.synthesize(heard.text, self.language))
        received, stats = self.line.transmit(audio)
        t0 = self.timer.now()
        transcript = self.stt.transcribe(mock_codec.to_pcm16(received), self.language)
        stt_s = self.timer.now() - t0
        complete = not _INCOMPLETE.search(heard.text)
        endpoint = MIN_ENDPOINTING_S if complete else MAX_ENDPOINTING_S
        barge: float | None = None
        false_int = False
        if heard.overlap or self._rng.random() < self.caller.persona.interruption_propensity:
            # Server-side: VAD detection, one jitter-buffer frame, TTS flush.
            barge = VAD_DETECT_S + 0.02 + TTS_FLUSH_S
            # Adaptive interruption: a backchannel resumes the agent; only a misheard one stops it.
            # The agent decides with guardrails.classify on what STT returned, so the metric
            # must use the same rule (an overlap of two words or fewer is a backchannel).
            false_int = (
                bool(BACKCHANNEL_ONLY.match(heard.text))
                and not classify(transcript.text, overlap=True).backchannel
            )
        metric = TurnMetrics(
            reference=heard.text,
            hypothesis=transcript.text,
            cer=char_error_rate(heard.text, transcript.text),
            wer=word_error_rate(heard.text, transcript.text),
            eos_to_first_audio_s=0.0,  # completed when the agent reply is ready
            false_cutoff=self._false_cutoff(heard.text),
            barge_in_stop_s=barge,
            false_interruption=false_int,
            line_delay_ms=stats.delay_ms,
        )
        self.metrics.append(metric)
        self._pending = (metric, self.timer.now(), endpoint, stt_s)
        return Heard(
            text=transcript.text,
            overlap=heard.overlap,
            stt_s=stt_s,
            endpoint_s=endpoint,
            confidence=transcript.confidence,
        )
