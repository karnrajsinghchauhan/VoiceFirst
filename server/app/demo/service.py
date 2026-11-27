"""Implements app.api.ports.Demo. Holds the demo's kill-switch state between runs."""

from __future__ import annotations

import hmac
import threading
from datetime import UTC, datetime, time, timedelta

from app.api.ports import DemoRun, DemoScenario, KillSwitchResult
from app.core.errors import AuthError, NotFoundError
from app.core.ids import new_id
from app.demo.engine import demo_settings, run_call, time_kill_switch
from app.demo.scenarios import SCENARIOS, build_event
from app.demo.settings import DemoSettings
from app.demo.timeline import build_run
from app.simulator.caller import Persona, load_personas

_IST = timedelta(hours=5, minutes=30)


def _call_time(now: datetime) -> datetime:
    """11:00 IST today, inside the 09:00-21:00 window whenever the demo is shown."""
    local_day = (now + _IST).date()
    return datetime.combine(local_day, time(11, 0), UTC) - _IST


class DemoService:
    def __init__(self, settings: DemoSettings) -> None:
        self._passcode = settings.passcode
        self._personas: dict[str, Persona] = {p.id: p for p in load_personas()}
        self._engine_settings = demo_settings()
        self._lock = threading.Lock()
        self._engaged = False

    def check_passcode(self, presented: str) -> None:
        if self._passcode is None:
            raise NotFoundError("demo is not enabled: AV_DEMO_PASSCODE is not set")
        if not hmac.compare_digest(presented.encode(), self._passcode.get_secret_value().encode()):
            raise AuthError("wrong demo passcode")

    def run(self, scenario: DemoScenario) -> DemoRun:
        spec = SCENARIOS[scenario]
        persona = self._personas[spec.persona_id]
        at = _call_time(datetime.now(UTC))
        event = build_event(self._engine_settings, spec, persona, at)
        with self._lock:
            run = run_call(self._engine_settings, event, persona, at, killed=self._engaged)
        return build_run(new_id("demo"), scenario, run, persona)

    def kill(self) -> KillSwitchResult:
        spec = SCENARIOS["failed_upi"]
        persona = self._personas[spec.persona_id]
        at = _call_time(datetime.now(UTC))
        event = build_event(self._engine_settings, spec, persona, at)
        with self._lock:
            stopped_in_ms = time_kill_switch(self._engine_settings, event, at)
            self._engaged = True
        return KillSwitchResult(engaged=True, stopped_in_ms=stopped_in_ms)

    def release(self) -> KillSwitchResult:
        with self._lock:
            self._engaged = False
        return KillSwitchResult(engaged=False, stopped_in_ms=0)
