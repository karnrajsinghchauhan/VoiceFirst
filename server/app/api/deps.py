"""Request-scoped dependencies: the wired services, a unit-of-work session, and the caller's principal."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CollectorRegistry, Counter, Gauge
from sqlalchemy.orm import Session, sessionmaker

from app.admin import apikeys
from app.admin.oidc import OidcVerifier
from app.admin.rbac import Permission, Principal, authorize, resolve_token
from app.api.ports import CampaignService, IncidentService, Simulator
from app.core.bus import EventBus
from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import transaction
from app.core.errors import AuthError
from app.handoff.transfer import HumanQueue
from app.postcall.crypto import DataCipher
from app.providers.base import CrmProvider
from app.rights.workflow import RightsSlaSettings


@dataclass(frozen=True)
class Metrics:
    registry: CollectorRegistry
    requests: Counter
    kill_switch: Gauge


def make_metrics() -> Metrics:
    # A registry per app keeps tests isolated; production runs one app per process.
    registry = CollectorRegistry()
    return Metrics(
        registry=registry,
        requests=Counter(
            "av_http_requests_total", "HTTP requests", ["route", "status"], registry=registry
        ),
        kill_switch=Gauge(
            "av_kill_switch_engaged", "1 when the kill switch is engaged", registry=registry
        ),
    )


@dataclass(frozen=True)
class ApiDeps:
    settings: Settings
    session_factory: sessionmaker[Session]
    bus: EventBus
    clock: Clock
    cipher: DataCipher
    rights_sla: RightsSlaSettings
    simulator: Simulator
    campaigns: CampaignService
    incidents: IncidentService
    human_queue: HumanQueue
    crm: CrmProvider
    metrics: Metrics
    oidc: OidcVerifier | None


def get_deps(request: Request) -> ApiDeps:
    deps = request.app.state.deps
    assert isinstance(deps, ApiDeps)
    return deps


Deps = Annotated[ApiDeps, Depends(get_deps)]


def get_session(deps: Deps) -> Iterator[Session]:
    with transaction(deps.session_factory) as session:
        yield session


Db = Annotated[Session, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


def get_principal(
    deps: Deps,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None:
        raise AuthError("missing bearer token")
    token = credentials.credentials
    if token.startswith(apikeys.PREFIX):
        with transaction(deps.session_factory) as session:
            return apikeys.authenticate(session, token, deps.clock.now())
    if token.count(".") == 2:
        if deps.oidc is None:
            raise AuthError("SSO is not configured for this tenant")
        return deps.oidc.verify(token)
    return resolve_token(deps.settings.api_tokens, token)


def require(permission: Permission) -> Callable[[Principal], Principal]:
    def _check(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        authorize(principal, permission)
        return principal

    return _check
