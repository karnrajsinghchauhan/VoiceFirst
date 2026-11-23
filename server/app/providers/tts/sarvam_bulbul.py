"""Sarvam Bulbul text-to-speech adapter. Thin httpx client; never called in tests (no keys).

Stock voices only, licensed for commercial telephony and recorded in
docs/licences.md (REQ-AI-02). Shape to be verified on the first real call.
"""

from __future__ import annotations

import base64
import io
import os
import wave
from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.core.types import Language

_URL = "https://api.sarvam.ai/text-to-speech"
_LANG_CODE = {"hi": "hi-IN", "hinglish": "hi-IN", "en": "en-IN", "unknown": "hi-IN"}


@dataclass
class SarvamBulbulTts:
    api_key: str
    model_id: str
    voice_id: str
    voice_gender: Literal["female", "male"]
    timeout_s: float = 3.0
    name: str = "sarvam_bulbul"

    @classmethod
    def from_env(cls, voice_id: str, voice_gender: Literal["female", "male"]) -> SarvamBulbulTts:
        key, model = os.environ.get("SARVAM_API_KEY"), os.environ.get("AV_SARVAM_TTS_MODEL")
        if not key or not model:
            raise ConfigError(
                "SARVAM_API_KEY and AV_SARVAM_TTS_MODEL must be set for tts=sarvam_bulbul"
            )
        return cls(key, model, voice_id, voice_gender)

    def synthesize(self, text: str, language: Language) -> bytes:
        body = {
            "text": text,
            "target_language_code": _LANG_CODE[language],
            "speaker": self.voice_id,
            "model": self.model_id,
            "speech_sample_rate": 8000,
        }
        try:
            resp = httpx.post(
                _URL,
                json=body,
                timeout=self.timeout_s,
                headers={"api-subscription-key": self.api_key},
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("sarvam tts timed out") from exc
        if resp.status_code != 200:
            raise ProviderError(f"sarvam tts returned {resp.status_code}")
        wav = base64.b64decode(resp.json()["audios"][0])
        with wave.open(io.BytesIO(wav), "rb") as w:
            if w.getframerate() != 8000 or w.getsampwidth() != 2:
                raise ProviderError("sarvam tts returned audio that is not 8 kHz 16-bit")
            return w.readframes(w.getnframes())
