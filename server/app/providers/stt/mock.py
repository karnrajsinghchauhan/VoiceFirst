"""Deterministic mock STT: mock_codec audio -> text, seeded latency on a SimTimer."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import ProviderError
from app.core.types import Language
from app.providers import mock_codec
from app.providers.base import Transcript
from app.providers.latency import LatencyModel, SimTimer
from app.voice.guardrails import detect_language


@dataclass
class MockStt:
    timer: SimTimer
    latency: LatencyModel
    name: str = "mock"
    model_id: str = "mock-fsk-stt-v1"
    fail: bool = False

    def transcribe(self, pcm16_8khz: bytes, language_hint: Language) -> Transcript:
        if self.fail:
            raise ProviderError("mock STT unavailable")
        self.timer.advance(self.latency.sample())
        text, erasures = mock_codec.decode(mock_codec.from_pcm16(pcm16_8khz))
        return Transcript(text=text, language=detect_language(text), confidence=1.0 - erasures)
