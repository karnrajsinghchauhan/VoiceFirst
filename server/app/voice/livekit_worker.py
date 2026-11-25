"""LiveKit Agents 1.8.13 adapter (D-004, D-102). Imported only with the `voice` extra.

Every name used here was checked against the installed livekit-agents 1.8.13.
Turn handling is pinned explicitly because defaults differ between dev, cloud
and self-hosted (brief 7.2):
- turn detection: the local multilingual end-of-utterance model from
  livekit-plugins-turn-detector 1.8.13. The inference-gateway TurnDetector is
  not used: it sends audio-derived text to LiveKit Cloud (residency, P4) and
  its `local_fallback` is a runtime fallback (rule 6.1).
- endpointing: fixed, 0.5 s min / 1.6 s max (matches simulator/audio.py).
- interruption: mode "adaptive" (backchannels resume speech), 0.2 s minimum,
  resume on false interruption.
- preemptive generation on, so the LLM runs during endpointing.

Bridging our STT/TTS/LLM provider interfaces into LiveKit's plugin classes is
M8 work, blocked on provider keys; `entrypoint` raises until then.
"""

from __future__ import annotations

from typing import Any

from livekit.agents import AgentServer, AgentSession, JobContext, TurnHandlingOptions
from livekit.agents.voice.turn import (
    EndpointingOptions,
    InterruptionOptions,
    PreemptiveGenerationOptions,
)

from app.core.errors import NotBuiltYetError
from app.voice.turn_config import (
    INTERRUPTION_MODE,
    MAX_ENDPOINTING_S,
    MIN_ENDPOINTING_S,
    MIN_INTERRUPTION_S,
)

LIVEKIT_AGENTS_VERSION = "1.8.13"


def turn_handling(turn_detector: Any) -> TurnHandlingOptions:
    return TurnHandlingOptions(
        turn_detection=turn_detector,
        endpointing=EndpointingOptions(
            mode="fixed", min_delay=MIN_ENDPOINTING_S, max_delay=MAX_ENDPOINTING_S
        ),
        interruption=InterruptionOptions(
            enabled=True,
            mode=INTERRUPTION_MODE,
            min_duration=MIN_INTERRUPTION_S,
            min_words=0,
            resume_false_interruption=True,
            false_interruption_timeout=1.0,
            discard_audio_if_uninterruptible=True,
        ),
        preemptive_generation=PreemptiveGenerationOptions(enabled=True, preemptive_tts=False),
    )


def local_turn_detector() -> Any:
    from livekit.plugins.turn_detector.multilingual import MultilingualModel

    return MultilingualModel()


def build_session(turn_detector: Any) -> AgentSession[None]:
    return AgentSession(turn_handling=turn_handling(turn_detector))


server = AgentServer()


@server.rtc_session(agent_name="agoda-voice-outbound")
async def entrypoint(ctx: JobContext) -> None:
    # Outbound flow once M8 lands: start AMD before creating the SIP participant
    #   async with AMD(session, llm=None) as detector:
    #       await ctx.api.sip.create_sip_participant(...)
    #       result = await detector.execute()
    # then run voice.agent.Conversation turns over the session.
    raise NotBuiltYetError("AV-M8: bridge providers into LiveKit STT/TTS/LLM (blocked: no keys)")
