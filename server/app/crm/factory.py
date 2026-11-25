"""Builds the one CRM provider named by config at boot (7.7). Unknown or unbuilt names fail startup."""

from __future__ import annotations

from app.core.config import Settings
from app.core.errors import ProviderNotBuiltError
from app.providers.base import CrmProvider
from app.providers.crm.mock import MockCrm
from app.providers.crm.zendesk import ZendeskCrm, ZendeskSettings


def make_crm(settings: Settings) -> CrmProvider:
    if settings.crm == "mock":
        return MockCrm()
    if settings.crm == "zendesk":
        return ZendeskCrm(ZendeskSettings())
    raise ProviderNotBuiltError(f"CRM provider {settings.crm!r} is not built yet (ticket AV-CRM-2)")
