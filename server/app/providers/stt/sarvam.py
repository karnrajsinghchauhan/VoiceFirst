"""Sarvam speech-to-text adapter. Thin httpx client; never called in tests (no keys).

Endpoint and field names follow Sarvam's public REST docs as understood at
build time; verify on the first real call (counted against the 20-call cap).
"""

from __future__ import annotations

import io
import os
import wave
from dataclasses import dataclass

import httpx

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.core.types import Language
from app.providers.base import Transcript

_URL = "https://api.sarvam.ai/speech-to-text"
_LANG_CODE = {"hi": "hi-IN", "hinglish": "hi-IN", "en": "en-IN", "unknown": "unknown"}


def pcm_to_wav(pcm16_8khz: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(pcm16_8khz)
    return buf.getvalue()


@dataclass
class SarvamStt:
    api_key: str
    model_id: str
    timeout_s: float = 3.0
    name: str = "sarvam"

    @classmethod
    def from_env(cls) -> SarvamStt:
        key, model = os.environ.get("SARVAM_API_KEY"), os.environ.get("AV_SARVAM_STT_MODEL")
        if not key or not model:
            raise ConfigError("SARVAM_API_KEY and AV_SARVAM_STT_MODEL must be set for stt=sarvam")
        return cls(key, model)

    def transcribe(self, pcm16_8khz: bytes, language_hint: Language) -> Transcript:
        try:
            resp = httpx.post(
                _URL,
                timeout=self.timeout_s,
                headers={"api-subscription-key": self.api_key},
                data={"model": self.model_id, "language_code": _LANG_CODE[language_hint]},
                files={"file": ("turn.wav", pcm_to_wav(pcm16_8khz), "audio/wav")},
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("sarvam stt timed out") from exc
        if resp.status_code != 200:
            raise ProviderError(f"sarvam stt returned {resp.status_code}")
        body = resp.json()
        code = body.get("language_code") or ""
        language: Language = (
            "en" if code.startswith("en") else "hi" if code.startswith("hi") else "unknown"
        )
        return Transcript(text=body["transcript"], language=language, confidence=1.0)
