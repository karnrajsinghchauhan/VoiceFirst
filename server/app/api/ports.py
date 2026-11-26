"""Services the API depends on but does not own. The lead wires real implementations in app/wiring.

Each port returns the view models below; those models are the HTTP contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.core.types import Language, Purpose


class _View(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TranscriptLine(_View):
    speaker: Literal["agent", "customer"]
    text: str


class SimulationResult(_View):
    persona: str
    seed: int
    purpose: Purpose
    outcome: str
    tools_called: list[str]
    transcript: list[TranscriptLine]
    assertions_passed: bool
    trace_id: str


class Simulator(Protocol):
    def simulate(
        self, persona: str, seed: int, purpose: Purpose, language: Language
    ) -> SimulationResult: ...


class CampaignView(_View):
    campaign_id: str
    purpose: Purpose
    status: Literal["active", "paused"]
    queued: int
    dialled: int
    held_out: int


class CampaignService(Protocol):
    def list_campaigns(self) -> list[CampaignView]: ...

    def pause(self, campaign_id: str, actor: str, reason: str) -> CampaignView: ...

    def resume(self, campaign_id: str, actor: str, reason: str) -> CampaignView: ...


IncidentKind = Literal["security", "data_breach", "telecom_complaint", "other"]


class IncidentView(_View):
    incident_id: str
    kind: IncidentKind
    summary: str
    detected_at: datetime
    cert_in_due_at: datetime | None
    board_report_due_at: datetime | None
    status: Literal["open", "reported", "closed"]


class IncidentService(Protocol):
    def list_incidents(self) -> list[IncidentView]: ...

    def open_incident(
        self, kind: IncidentKind, summary: str, detected_at: datetime, actor: str
    ) -> IncidentView: ...


DemoScenario = Literal[
    "failed_upi", "confirmation", "angry_refund", "stop_calling", "child_answers", "card_number"
]
DemoEventKind = Literal[
    "holdout", "gate", "clearance", "disclosure", "tool", "whatsapp", "crm", "qa", "cost", "end"
]


class DemoEvent(_View):
    t_ms: int
    kind: DemoEventKind
    label: str
    status: Literal["pass", "fail", "info"]
    detail: dict[str, str | int | None]


class DemoTurn(_View):
    speaker: Literal["agent", "customer"]
    text: str
    t_ms: int


class DemoWhatsApp(_View):
    template: str
    language: str
    body: str


class DemoTicket(_View):
    ticket_id: str
    subject: str
    priority: str


class DemoCheck(_View):
    name: str
    passed: bool


class DemoQa(_View):
    score: int
    checks: list[DemoCheck]


class DemoCost(_View):
    telephony: int
    stt: int
    tts: int
    llm: int
    whatsapp: int
    total: int


class DemoLatency(_View):
    p50: int
    p95: int
    per_turn: list[int]


class DemoRun(_View):
    run_id: str
    scenario: DemoScenario
    mode: Literal["text"]
    method: str
    events: list[DemoEvent]
    transcript: list[DemoTurn]
    whatsapp_preview: DemoWhatsApp | None
    crm_ticket: DemoTicket | None
    qa: DemoQa
    cost_paise: DemoCost
    latency_ms: DemoLatency


class KillSwitchResult(_View):
    engaged: bool
    # Engine time from the engage request to the dispatcher refusing the next dial.
    stopped_in_ms: int


class Demo(Protocol):
    def run(self, scenario: DemoScenario) -> DemoRun: ...

    def kill(self) -> KillSwitchResult: ...

    def release(self) -> KillSwitchResult: ...

    def check_passcode(self, presented: str) -> None: ...
