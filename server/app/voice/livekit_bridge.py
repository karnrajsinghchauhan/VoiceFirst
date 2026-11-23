"""M8 media bridge: our Conversation speaks and listens through a LiveKit AgentSession (D-502).

The Conversation is synchronous and owns every decision. LiveKit owns only audio: VAD,
turn detection, STT in, TTS out, barge-in. The session's Agent therefore has no LLM; we
call `session.say(text)` for each agent turn and wait for the caller's final transcript.

Threading: the dispatcher thread runs the Conversation; the AgentSession lives on its own
asyncio loop in a daemon thread. `listen()` hands one turn to that loop and blocks on the
result, so a slow or dead media path surfaces as a typed timeout, never a hang.

Pinned against livekit-agents 1.8.13 (AgentSession.say, the user_input_transcribed event,
SpeechHandle.interrupted). Exercised end to end only with keys (tests/voice/test_livekit_bridge).
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any, TypeVar

from app.core.config import Settings
from app.core.errors import ProviderNotBuiltError, ProviderTimeoutError
from app.core.types import Language
from app.providers.livekit_settings import LiveKitSettings
from app.voice.agent import Heard

T = TypeVar("T")

# Sarvam takes BCP-47 India locales; Hinglish is transcribed and spoken as hi-IN.
STT_LANGUAGE: dict[Language, str] = {
    "hi": "hi-IN",
    "hinglish": "hi-IN",
    "en": "en-IN",
    "unknown": "unknown",
}
TTS_LANGUAGE: dict[Language, str] = {
    "hi": "hi-IN",
    "hinglish": "hi-IN",
    "en": "en-IN",
    "unknown": "hi-IN",
}
# How long we wait for the caller to start and finish a turn after our line ends.
DEFAULT_TURN_TIMEOUT_S = 8.0
# Margin on top of the turn timeout for our own speech to play out.
SAY_BUDGET_S = 20.0


@dataclass
class TurnCapture:
    """What one caller turn produced on the media path, before mapping to Heard."""

    finals: list[str] = field(default_factory=list)
    interrupted: bool = False
    said_at: float = 0.0
    first_final_at: float | None = None


def heard_from(capture: TurnCapture) -> Heard:
    """Pure mapping. Silence (no final transcript) is an empty turn, which the agent handles."""
    text = " ".join(t.strip() for t in capture.finals if t.strip())
    endpoint_s = (capture.first_final_at - capture.said_at) if capture.first_final_at else 0.0
    # LiveKit's session event carries no STT confidence, so we cannot claim low confidence
    # from it; the agent's own low-confidence path is driven by the STT provider when it
    # reports one (D-504).
    return Heard(text=text, overlap=capture.interrupted, endpoint_s=max(0.0, endpoint_s))


def livekit_plugins(settings: Settings, language: Language) -> dict[str, Any]:
    """The LiveKit plugin instances for the configured providers. One per role; no fallbacks."""
    from livekit.plugins import sarvam, silero

    if settings.stt != "sarvam":
        raise ProviderNotBuiltError(f"LiveKit bridge has no STT plugin for stt={settings.stt}")
    if settings.tts != "sarvam_bulbul":
        raise ProviderNotBuiltError(f"LiveKit bridge has no TTS plugin for tts={settings.tts}")
    return {
        "stt": sarvam.STT(language=STT_LANGUAGE[language]),
        "tts": sarvam.TTS(target_language_code=TTS_LANGUAGE[language], speaker=settings.voice_id),
        # Telephone audio is 8 kHz; the VAD model is told so rather than resampling twice.
        "vad": silero.VAD.load(sample_rate=8000),
    }


class LiveKitListener:
    """The customer side of a real call. Implements app.voice.agent.Listener."""

    def __init__(
        self,
        session: Any,
        loop: asyncio.AbstractEventLoop,
        turn_timeout_s: float = DEFAULT_TURN_TIMEOUT_S,
    ) -> None:
        self._session = session
        self._loop = loop
        self._turn_timeout_s = turn_timeout_s
        self._finals: asyncio.Queue[tuple[str, float]] = asyncio.Queue()
        session.on("user_input_transcribed", self._on_transcript)

    def _on_transcript(self, event: Any) -> None:
        # Runs on the session loop. Interim results are ignored: only finals end a turn.
        if event.is_final:
            self._finals.put_nowait((event.transcript, time.monotonic()))

    async def _turn(self, agent_text: str) -> TurnCapture:
        while not self._finals.empty():  # anything heard before our line belongs to no turn
            self._finals.get_nowait()
        capture = TurnCapture(said_at=time.monotonic())
        handle = self._session.say(agent_text, allow_interruptions=True)
        await handle.wait_for_playout()
        capture.interrupted = bool(handle.interrupted)
        try:
            text, at = await asyncio.wait_for(self._finals.get(), self._turn_timeout_s)
        except TimeoutError:
            return capture
        capture.finals.append(text)
        capture.first_final_at = at
        while not self._finals.empty():
            capture.finals.append(self._finals.get_nowait()[0])
        return capture

    def _run(self, coro: Coroutine[Any, Any, T], budget_s: float) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=budget_s)
        except TimeoutError as exc:
            future.cancel()
            raise ProviderTimeoutError("LiveKit media path did not complete the turn") from exc

    def listen(self, act: str, agent_text: str) -> Heard:
        capture = self._run(self._turn(agent_text), SAY_BUDGET_S + self._turn_timeout_s)
        return heard_from(capture)


class LoopThread:
    """An asyncio loop on a daemon thread; the LiveKit room and session live here."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self.loop.run_forever, daemon=True, name="livekit-bridge"
        )
        self._thread.start()

    def run(self, coro: Coroutine[Any, Any, T], timeout_s: float) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout_s)
        except TimeoutError as exc:
            future.cancel()
            raise ProviderTimeoutError("LiveKit did not respond in time") from exc

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)


# The callee must answer within the SIP ringing timeout (30 s) plus connect overhead.
JOIN_TIMEOUT_S = 40.0
CALLEE_IDENTITY = "callee"


class LiveKitMediaBridge:
    """Builds a LiveKitListener for a placed call. Construction fails at boot without keys."""

    def __init__(self, settings: Settings, livekit: LiveKitSettings) -> None:
        livekit.require_complete()
        self._settings = settings
        self._lk = livekit

    def agent_token(self, room_name: str) -> str:
        from livekit import api as lk

        grants = lk.VideoGrants(room_join=True, room=room_name, agent=True)
        token = lk.AccessToken(self._lk.api_key, self._lk.api_secret).with_identity("av-agent")
        return token.with_grants(grants).to_jwt()

    async def _join(
        self, room_name: str, language: Language, loop: asyncio.AbstractEventLoop
    ) -> LiveKitListener:
        from livekit import rtc
        from livekit.agents import Agent, AgentSession

        from app.voice.livekit_worker import local_turn_detector, turn_handling

        room = rtc.Room(loop=loop)
        await room.connect(self._lk.url, self.agent_token(room_name))
        plugins = livekit_plugins(self._settings, language)
        session: AgentSession[None] = AgentSession(
            turn_handling=turn_handling(local_turn_detector()), **plugins
        )
        # No LLM and no instructions: every word the agent says comes from our Conversation.
        await session.start(Agent(instructions=""), room=room)
        joined = asyncio.Event()
        if CALLEE_IDENTITY in {p.identity for p in room.remote_participants.values()}:
            joined.set()

        def on_connected(participant: Any) -> None:
            if participant.identity == CALLEE_IDENTITY:
                joined.set()

        room.on("participant_connected", on_connected)
        await asyncio.wait_for(joined.wait(), JOIN_TIMEOUT_S)
        return LiveKitListener(session, loop)

    def listener_for(self, room_name: str, language: Language) -> LiveKitListener:
        runner = LoopThread()
        return runner.run(self._join(room_name, language, runner.loop), JOIN_TIMEOUT_S + 5.0)
