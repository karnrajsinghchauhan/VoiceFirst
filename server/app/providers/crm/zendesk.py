"""Zendesk CRM adapter (2.4: Agoda's partner helpdesk is on Zendesk). Tickets API v2.

Tickets carry no customer PII: the requester is the API user and the customer
is referenced only by an opaque `external_id`. The handoff summary is posted as
an internal (non-public) comment.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.providers.base import CrmTicket

ZendeskPriority = Literal["low", "normal", "high", "urgent"]
_PRIORITIES: frozenset[str] = frozenset({"low", "normal", "high", "urgent"})


class ZendeskSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AV_ZENDESK_", extra="ignore", frozen=True)

    subdomain: str = ""
    email: str = ""
    api_token: str = ""
    timeout_seconds: float = 10.0

    def require_complete(self) -> None:
        missing = [k for k in ("subdomain", "email", "api_token") if not getattr(self, k)]
        if missing:
            raise ConfigError(f"zendesk settings missing: {missing}")


class _TicketBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int


class _TicketResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ticket: _TicketBody


class ZendeskCrm:
    name = "zendesk"

    def __init__(self, settings: ZendeskSettings, transport: httpx.BaseTransport | None = None):
        settings.require_complete()
        self._base = f"https://{settings.subdomain}.zendesk.com"
        self._client = httpx.Client(
            base_url=self._base,
            auth=(f"{settings.email}/token", settings.api_token),
            timeout=settings.timeout_seconds,
            transport=transport,
        )

    def create_ticket(
        self, subject: str, body: str, requester_ref: str, tags: list[str], priority: str
    ) -> CrmTicket:
        if priority not in _PRIORITIES:
            raise ProviderError(f"zendesk priority must be one of {sorted(_PRIORITIES)}")
        payload = {
            "ticket": {
                "subject": subject,
                "comment": {"body": body, "public": False},
                "external_id": requester_ref,
                "tags": tags,
                "priority": priority,
            }
        }
        response = self._request("POST", "/api/v2/tickets.json", payload)
        try:
            ticket_id = str(_TicketResponse.model_validate_json(response.content).ticket.id)
        except ValidationError as exc:
            raise ProviderError("zendesk returned an unexpected ticket body") from exc
        return CrmTicket(ticket_id=ticket_id, url=f"{self._base}/agent/tickets/{ticket_id}")

    def add_note(self, ticket_id: str, body: str) -> None:
        payload = {"ticket": {"comment": {"body": body, "public": False}}}
        self._request("PUT", f"/api/v2/tickets/{ticket_id}.json", payload)

    def _request(self, method: str, path: str, payload: Mapping[str, object]) -> httpx.Response:
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"zendesk {method} {path} timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"zendesk {method} {path} failed: {exc}") from exc
        if response.status_code >= 300:
            raise ProviderError(f"zendesk {method} {path} returned {response.status_code}")
        return response
