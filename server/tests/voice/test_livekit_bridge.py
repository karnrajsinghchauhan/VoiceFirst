"""The M8 bridge without a LiveKit server: event mapping, threading, timeouts, boot checks."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import pytest

from app.core.errors import ConfigError, ProviderNotBuiltError, ProviderTimeoutError
from app.providers.livekit_settings import LiveKitSettings
from app.voice.livekit_bridge import (
    LiveKitListener,
    LiveKitMediaBridge,
    LoopThread,
    TurnCapture,
    heard_from,
    livekit_plugins,
)
from tests.factories import make_settings


@dataclass
class _Event:
    transcript: str
    is_final: bool


class _Handle:
    def __init__(self, interrupted: bool) -> None:
        self.interrupted = interrupted

    async def wait_for_playout(self) -> None:
        await asyncio.sleep(0)


class FakeSession:
    """Stands in for AgentSession: records say() and plays scripted caller transcripts."""

    def __init__(self, replies: list[list[_Event]], interrupted: bool = False) -> None:
        self._replies = replies
        self._interrupted = interrupted
        self.said: list[str] = []
        self._handlers: dict[str, Any] = {}

    def on(self, name: str, handler: Any) -> None:
        self._handlers[name] = handler

    def say(self, text: str, *, allow_interruptions: bool) -> _Handle:
        self.said.append(text)
        events = self._replies.pop(0) if self._replies else []
        loop = asyncio.get_running_loop()
        for ev in events:
            loop.call_later(0.01, self._handlers["user_input_transcribed"], ev)
        return _Handle(self._interrupted)


def test_heard_maps_finals_and_overlap():
    heard = heard_from(
        TurnCapture(
            finals=["haan", " bhej do "], interrupted=True, said_at=10.0, first_final_at=11.5
        )
    )
    assert heard.text == "haan bhej do" and heard.overlap is True and heard.endpoint_s == 1.5


def test_silence_is_an_empty_turn():
    assert heard_from(TurnCapture(said_at=1.0)).text == ""


def test_listener_speaks_then_returns_only_final_transcripts():
    loop = LoopThread()
    session = FakeSession([[_Event("ha", False), _Event("haan bhej do", True)]])
    listener = LiveKitListener(session, loop.loop, turn_timeout_s=1.0)
    heard = listener.listen("j1_ask", "Kya main link bhej doon?")
    loop.stop()
    assert session.said == ["Kya main link bhej doon?"]
    assert heard.text == "haan bhej do" and heard.overlap is False


def test_listener_reports_barge_in():
    loop = LoopThread()
    listener = LiveKitListener(
        FakeSession([[_Event("agent chahiye", True)]], interrupted=True),
        loop.loop,
        turn_timeout_s=1.0,
    )
    heard = listener.listen("j1_ask", "...")
    loop.stop()
    assert heard.overlap is True and heard.text == "agent chahiye"


def test_no_reply_within_turn_timeout_is_silence():
    loop = LoopThread()
    heard = LiveKitListener(FakeSession([[]]), loop.loop, turn_timeout_s=0.05).listen("a", "b")
    loop.stop()
    assert heard.text == ""


def test_stalled_media_path_raises_typed_timeout():
    loop = LoopThread()
    with pytest.raises(ProviderTimeoutError):
        loop.run(asyncio.sleep(5), timeout_s=0.05)
    loop.stop()


def test_bridge_refuses_to_boot_without_keys():
    with pytest.raises(ConfigError):
        LiveKitMediaBridge(make_settings(), LiveKitSettings(url="", api_key="", api_secret=""))


def test_agent_token_grants_only_this_room():
    import jwt

    lk = LiveKitSettings(url="wss://lk.example.invalid", api_key="k", api_secret="s" * 32)
    token = LiveKitMediaBridge(make_settings(), lk).agent_token("call_abc")
    claims = jwt.decode(token, "s" * 32, algorithms=["HS256"])
    assert claims["video"]["room"] == "call_abc" and claims["video"]["roomJoin"] is True


def test_only_sarvam_plugins_are_bridged():
    with pytest.raises(ProviderNotBuiltError):
        livekit_plugins(make_settings(), "hinglish")


@pytest.mark.skipif(
    not (os.environ.get("LIVEKIT_API_KEY") and os.environ.get("SARVAM_API_KEY")),
    reason="needs LiveKit and Sarvam keys (spending gate); builds real plugins, places no call",
)
def test_real_plugins_construct_with_keys():
    plugins = livekit_plugins(make_settings(stt="sarvam", tts="sarvam_bulbul"), "hinglish")
    assert set(plugins) == {"stt", "tts", "vad"}
