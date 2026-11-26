"""Demo-owned settings. The passcode keeps /demo private; without one the demo refuses every call."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AV_DEMO_", extra="ignore", frozen=True)

    passcode: SecretStr | None = None
