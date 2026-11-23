"""Deterministic test doubles for the API ports. Used by tests and by the OpenAPI export.

They are never wired in production: app.wiring replaces them, and these return
fixed data that would be obviously wrong in a live console.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import ApiDeps, make_metrics
from app.api.ports import (
    CampaignView,
    IncidentKind,
    IncidentView,
    SimulationResult,
    TranscriptLine,
)
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.types import Language, Purpose
from app.handoff.transfer import InMemoryHumanQueue
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.providers.crm.mock import MockCrm
from app.rights.workflow import RightsSlaSettings


class StubSimulator:
    def simulate(
        self, persona: str, seed: int, purpose: Purpose, language: Language
    ) -> SimulationResult:
        return SimulationResult(
            persona=persona,
            seed=seed,
            purpose=purpose,
            outcome="link_sent",
            tools_called=["send_payment_link", "end_call"],
            transcript=[
                TranscriptLine(
                    speaker="agent",
                    text="Namaste ji, main Agoda ki taraf se ek AI "
                    "assistant bol rahi hoon, aur yeh call record ho rahi hai.",
                ),
                TranscriptLine(speaker="customer", text="haan bhej do"),
            ],
            assertions_passed=True,
            trace_id="0" * 32,
        )


@dataclass
class StubCampaigns:
    campaigns: dict[str, CampaignView] = field(
        default_factory=lambda: {
            "cmp_j1": CampaignView(
                campaign_id="cmp_j1", purpose="J1", status="active", queued=0, dialled=0, held_out=0
            ),
        }
    )

    def list_campaigns(self) -> list[CampaignView]:
        return list(self.campaigns.values())

    def pause(self, campaign_id: str, actor: str, reason: str) -> CampaignView:
        return self._set(campaign_id, "paused")

    def resume(self, campaign_id: str, actor: str, reason: str) -> CampaignView:
        return self._set(campaign_id, "active")

    def _set(self, campaign_id: str, status: str) -> CampaignView:
        current = self.campaigns.get(campaign_id)
        if current is None:
            raise NotFoundError(f"no campaign {campaign_id}")
        updated = current.model_copy(update={"status": status})
        self.campaigns[campaign_id] = updated
        return updated


@dataclass
class StubIncidents:
    incidents: list[IncidentView] = field(default_factory=list)

    def list_incidents(self) -> list[IncidentView]:
        return list(self.incidents)

    def open_incident(
        self, kind: IncidentKind, summary: str, detected_at: datetime, actor: str
    ) -> IncidentView:
        view = IncidentView(
            incident_id=f"inc_{len(self.incidents) + 1}",
            kind=kind,
            summary=summary,
            detected_at=detected_at,
            cert_in_due_at=detected_at + timedelta(hours=6) if kind == "security" else None,
            board_report_due_at=detected_at + timedelta(hours=72)
            if kind == "data_breach"
            else None,
            status="open",
        )
        self.incidents.append(view)
        return view


def build_stub_deps(
    settings: Settings,
    session_factory: sessionmaker[Session],
    bus: EventBus,
    clock: Clock,
) -> ApiDeps:
    """ApiDeps with every port stubbed. For tests and the OpenAPI export only."""
    return ApiDeps(
        settings=settings,
        session_factory=session_factory,
        bus=bus,
        clock=clock,
        cipher=DataCipher(PostcallSettings().data_key),
        rights_sla=RightsSlaSettings(),
        simulator=StubSimulator(),
        campaigns=StubCampaigns(),
        incidents=StubIncidents(),
        human_queue=InMemoryHumanQueue(),
        crm=MockCrm(),
        metrics=make_metrics(),
    )
