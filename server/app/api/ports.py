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
