"""Deterministic mock TTS: text -> mock_codec audio, seeded latency on a SimTimer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.core.errors import ProviderError
from app.core.types import Language
from app.providers import mock_codec
from app.providers.latency import LatencyModel, SimTimer


@dataclass
class MockTts:
    timer: SimTimer
    latency: LatencyModel
    voice_id: str = "mock-female-1"
    voice_gender: Literal["female", "male"] = "female"
    name: str = "mock"
    model_id: str = "mock-fsk-tts-v1"
    fail: bool = False
    chars: int = field(default=0)

    def synthesize(self, text: str, language: Language) -> bytes:
        if self.fail:
            raise ProviderError("mock TTS unavailable")
        # Time to first audio chunk; the codec length is not a speech duration.
        self.timer.advance(self.latency.sample())
        self.chars += len(text)
        return mock_codec.to_pcm16(mock_codec.encode(text))
