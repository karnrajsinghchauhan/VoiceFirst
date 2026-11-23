"""Builds exactly one provider per role from Settings at boot (rule 6.2).

Unknown or unbuilt names fail here, at startup, with a typed error; nothing is
chosen at runtime and there is no fallback chain. Real providers read their
API keys from the environment (never from config files) and raise ConfigError
at boot when a key is missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import ProviderNotBuiltError
from app.crm.factory import make_crm
from app.providers.base import (
    CrmProvider,
    LlmProvider,
    SttProvider,
    TelephonyProvider,
    TtsProvider,
    WhatsAppProvider,
)
from app.providers.latency import LatencyModel, SimTimer
from app.providers.llm.mock import MockLlm
from app.providers.stt.mock import MockStt
from app.providers.telephony.mock import MockTelephony
from app.providers.tts.mock import MockTts
from app.providers.whatsapp.mock import MockWhatsApp
from app.voice.prompts import lint_gender

# Medians for the mock pipeline's simulated latency, seconds.
_MOCK_STT_S, _MOCK_LLM_S, _MOCK_TTS_S = 0.12, 0.35, 0.12


@dataclass(frozen=True)
class Providers:
    stt: SttProvider
    tts: TtsProvider
    llm: LlmProvider
    telephony: TelephonyProvider
    whatsapp: WhatsAppProvider
    crm: CrmProvider
    timer: SimTimer

    def model_ids(self) -> dict[str, str]:
        return {
            "stt": self.stt.model_id,
            "tts": self.tts.model_id,
            "llm": self.llm.model_id,
            "tts_voice": self.tts.voice_id,
        }


def _not_built(role: str, name: str, owner: str) -> ProviderNotBuiltError:
    return ProviderNotBuiltError(f"{role}={name} is a valid name but not built yet ({owner})")


def _stt(settings: Settings, timer: SimTimer, seed: int) -> SttProvider:
    if settings.stt == "mock":
        return MockStt(timer, LatencyModel(_MOCK_STT_S, 0.3, seed))
    if settings.stt == "sarvam":
        from app.providers.stt.sarvam import SarvamStt

        return SarvamStt.from_env()
    raise _not_built("stt", settings.stt, "see docs/licences.md for selfhosted [CD]")


def _tts(settings: Settings, timer: SimTimer, seed: int) -> TtsProvider:
    if settings.tts == "mock":
        return MockTts(
            timer,
            LatencyModel(_MOCK_TTS_S, 0.3, seed + 1),
            voice_id=settings.voice_id,
            voice_gender=settings.voice_gender,
        )
    if settings.tts == "sarvam_bulbul":
        from app.providers.tts.sarvam_bulbul import SarvamBulbulTts

        return SarvamBulbulTts.from_env(settings.voice_id, settings.voice_gender)
    raise _not_built("tts", settings.tts, "see docs/licences.md for selfhosted [CD]")


def _llm(settings: Settings, timer: SimTimer, seed: int) -> LlmProvider:
    if settings.llm == "mock":
        return MockLlm(timer, LatencyModel(_MOCK_LLM_S, 0.35, seed + 2))
    if settings.llm == "openai":
        from app.providers.llm.openai import OpenAiLlm

        return OpenAiLlm.from_env()
    if settings.llm == "anthropic":
        from app.providers.llm.anthropic import AnthropicLlm

        return AnthropicLlm.from_env()
    raise _not_built("llm", settings.llm, "vllm adapter is phase 2")


def build_providers(settings: Settings, seed: int = 0) -> Providers:
    # The prompt set must match the configured voice before any call is placed (REQ-AI-02).
    lint_gender(settings.voice_gender)
    timer = SimTimer()
    if settings.telephony != "mock":
        raise _not_built("telephony", settings.telephony, "telephony adapters are owned by W-A")
    if settings.whatsapp != "mock":
        raise _not_built("whatsapp", settings.whatsapp, "meta_cloud_api is owned by W-A")
    return Providers(
        stt=_stt(settings, timer, seed),
        tts=_tts(settings, timer, seed),
        llm=_llm(settings, timer, seed),
        telephony=MockTelephony(),
        whatsapp=MockWhatsApp(),
        crm=make_crm(settings),
        timer=timer,
    )
