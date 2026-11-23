"""Postcall-owned settings. The data key encrypts transcripts and audio references at rest (P4)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ProductionConfigError

# A fixed key for dev and tests only; production must supply AV_DATA_KEY from the secret store.
DEV_DATA_KEY = "ZGV2LWRhdGEta2V5LW5vdC1zZWNyZXQtMDAwMDAwMDA="


class PostcallSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AV_", extra="ignore", frozen=True)

    data_key: str = DEV_DATA_KEY


def validate_postcall_for_production(settings: PostcallSettings) -> None:
    if settings.data_key == DEV_DATA_KEY:
        raise ProductionConfigError("AV_DATA_KEY must be set from the secret store in production")
