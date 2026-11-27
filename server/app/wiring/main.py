"""Composition root for the HTTP API. The runtime itself is built in app.wiring.runtime."""

from __future__ import annotations

from fastapi import FastAPI

from app.admin.oidc import OidcVerifier, fetch_jwks
from app.api.app import create_app
from app.api.deps import ApiDeps, make_metrics
from app.campaigns.service import CampaignPort
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.demo.service import DemoService
from app.demo.settings import DemoSettings
from app.incidents.api_port import IncidentPort
from app.rights.workflow import RightsSlaSettings
from app.wiring.runtime import Runtime, build_dispatcher, build_runtime
from app.wiring.simulator_port import ScenarioSimulator

# Re-exported: tests and the dispatcher entry point import the runtime builders from here.
__all__ = ["Runtime", "api_app", "build_api", "build_dispatcher", "build_runtime"]


def _oidc(settings: Settings) -> OidcVerifier | None:
    if settings.oidc is None:
        return None
    return OidcVerifier(settings.oidc, fetch_jwks(settings.oidc.jwks_url))


def build_api(rt: Runtime) -> FastAPI:
    return create_app(
        ApiDeps(
            settings=rt.settings,
            session_factory=rt.session_factory,
            bus=rt.bus,
            clock=rt.clock,
            cipher=rt.cipher,
            rights_sla=RightsSlaSettings(),
            simulator=ScenarioSimulator(rt.settings),
            demo=DemoService(DemoSettings()),
            campaigns=CampaignPort(rt.session_factory, rt.settings.tenant_id, rt.clock),
            incidents=IncidentPort(rt.session_factory, rt.settings.tenant_id),
            human_queue=rt.human_queue,
            crm=rt.providers.crm,
            metrics=make_metrics(),
            oidc=_oidc(rt.settings),
        )
    )


def api_app() -> FastAPI:
    """uvicorn entry point: `uvicorn app.wiring.main:api_app --factory`."""
    configure_logging()
    return build_api(build_runtime(get_settings()))
