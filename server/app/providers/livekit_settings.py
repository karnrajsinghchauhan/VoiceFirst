"""LiveKit server credentials, shared by the SIP telephony client, the media bridge and webhooks.

Read from the environment only (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET), never from
config files, so keys stay in the platform secret store.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError


class LiveKitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LIVEKIT_", extra="ignore", frozen=True)

    url: str = ""
    api_key: str = ""
    api_secret: str = ""

    def require_complete(self) -> None:
        missing = [k for k in ("url", "api_key", "api_secret") if not getattr(self, k)]
        if missing:
            names = ["LIVEKIT_" + m.upper() for m in missing]
            raise ConfigError(f"LiveKit settings missing: {names}")

    @property
    def http_url(self) -> str:
        """The Twirp server API lives on the HTTP(S) origin of the ws(s) URL."""
        return self.url.replace("wss://", "https://").replace("ws://", "http://").rstrip("/")
