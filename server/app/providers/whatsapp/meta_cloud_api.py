"""WhatsApp Business Platform, Cloud API (Graph API). Templates, in-window text, quality rating.

Template parameters are sent by name (`parameter_name`), so the order of our params dict
can never put the amount where the link should be. Hinglish templates are registered under
the Latin-script `en_IN` locale (D-503, [CD] confirm with Meta template review).
"""

from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError, ProviderError, ProviderTimeoutError
from app.core.types import Language
from app.providers.base import SentMessage

GRAPH_BASE = "https://graph.facebook.com"
LOCALE: dict[Language, str] = {"hi": "hi", "en": "en", "hinglish": "en_IN", "unknown": "en_IN"}
_QUALITY: dict[str, Literal["high", "medium", "low"]] = {
    "GREEN": "high",
    "YELLOW": "medium",
    "RED": "low",
}


class MetaWhatsAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AV_META_", extra="ignore", frozen=True)

    access_token: str = ""
    phone_number_id: str = ""
    graph_version: str = "v21.0"
    app_secret: str = ""  # verifies inbound webhooks (X-Hub-Signature-256)
    verify_token: str = ""  # the GET handshake when subscribing the webhook
    timeout_seconds: float = 10.0

    def require_complete(self) -> None:
        keys = ("access_token", "phone_number_id", "app_secret", "verify_token")
        missing = [k for k in keys if not getattr(self, k)]
        if missing:
            raise ConfigError(
                f"Meta WhatsApp settings missing: {['AV_META_' + m.upper() for m in missing]}"
            )


class _MessageId(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str


class _SendResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    messages: list[_MessageId]


class _QualityResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    quality_rating: str


class MetaCloudWhatsApp:
    name = "meta_cloud_api"

    def __init__(
        self, settings: MetaWhatsAppSettings, transport: httpx.BaseTransport | None = None
    ) -> None:
        settings.require_complete()
        self._settings = settings
        self._client = httpx.Client(
            base_url=f"{GRAPH_BASE}/{settings.graph_version}",
            headers={"Authorization": f"Bearer {settings.access_token}"},
            timeout=settings.timeout_seconds,
            transport=transport,
        )

    def _request(self, method: str, path: str, body: dict[str, object] | None) -> httpx.Response:
        try:
            response = self._client.request(method, path, json=body)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"whatsapp {method} {path} timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"whatsapp {method} {path} failed: {exc}") from exc
        if response.status_code != 200:
            raise ProviderError(f"whatsapp {method} {path} returned {response.status_code}")
        return response

    def _send(self, body: dict[str, object]) -> SentMessage:
        path = f"/{self._settings.phone_number_id}/messages"
        response = self._request("POST", path, body)
        try:
            parsed = _SendResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise ProviderError("whatsapp returned an unexpected send body") from exc
        if not parsed.messages:
            raise ProviderError("whatsapp accepted the request but returned no message id")
        return SentMessage(provider_message_id=parsed.messages[0].id)

    def send_template(
        self, to_e164: str, template: str, language: Language, params: dict[str, str]
    ) -> SentMessage:
        parameters = [
            {"type": "text", "parameter_name": name, "text": value}
            for name, value in params.items()
        ]
        components = [{"type": "body", "parameters": parameters}] if parameters else []
        return self._send(
            {
                "messaging_product": "whatsapp",
                "to": to_e164.removeprefix("+"),
                "type": "template",
                "template": {
                    "name": template,
                    "language": {"code": LOCALE[language]},
                    "components": components,
                },
            }
        )

    def send_text(self, to_e164: str, text: str) -> SentMessage:
        return self._send(
            {
                "messaging_product": "whatsapp",
                "to": to_e164.removeprefix("+"),
                "type": "text",
                "text": {"body": text, "preview_url": False},
            }
        )

    def quality_rating(self) -> Literal["high", "medium", "low"]:
        path = f"/{self._settings.phone_number_id}?fields=quality_rating"
        response = self._request("GET", path, None)
        try:
            rating = _QualityResponse.model_validate_json(response.content).quality_rating
        except ValidationError as exc:
            raise ProviderError("whatsapp returned an unexpected quality body") from exc
        if rating not in _QUALITY:
            raise ProviderError(f"unknown WhatsApp quality rating {rating!r}")
        return _QUALITY[rating]
