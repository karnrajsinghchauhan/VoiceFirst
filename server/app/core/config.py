"""Configuration. Loaded once at boot from AV_* environment variables.

Every [CD] item from the brief is a field here with a safe default, never a
hard-coded truth. `validate_for_environment` fails startup on bad config.
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError, ProductionConfigError

SttName = Literal["mock", "sarvam", "elevenlabs", "selfhosted"]
TtsName = Literal["mock", "sarvam_bulbul", "elevenlabs", "selfhosted"]
LlmName = Literal["mock", "openai", "anthropic", "vllm"]
TelephonyName = Literal["mock", "plivo", "exotel"]
WhatsAppName = Literal["mock", "meta_cloud_api"]
CrmName = Literal["mock", "zendesk", "salesforce", "hubspot"]
BusName = Literal["memory", "kafka"]


class CallWindow(BaseModel):
    """REQ-TRAI-07. Recipient local time. May be narrowed, never widened."""

    start: time = time(9, 0)
    end: time = time(21, 0)

    @model_validator(mode="after")
    def _never_wider(self) -> CallWindow:
        if self.start < time(9, 0) or self.end > time(21, 0) or self.start >= self.end:
            raise ConfigError("call window must lie within 09:00-21:00 and start before end")
        return self


def _default_clis() -> dict[Literal["J1", "J2"], str]:
    return {"J1": "+911600200001", "J2": "+911601200001"}


class ComplianceSettings(BaseModel):
    # [CD] which series applies to Agoda's sender category.
    service_series: frozenset[Literal["1600", "1601"]] = frozenset({"1600", "1601"})
    promotional_series: frozenset[Literal["140"]] = frozenset({"140"})
    call_window: CallWindow = CallWindow()
    max_attempts_per_event: int = Field(default=2, ge=1, le=2)
    cooldown_hours: int = Field(default=24, ge=24)
    max_whatsapp_fallbacks_per_event: int = Field(default=1, ge=0, le=1)
    explicit_consent_days: int = Field(default=7, ge=1, le=7)
    inquiry_days: int = Field(default=7, ge=1, le=7)
    opt_out_lock_days: int = Field(default=90, ge=90)
    complaint_window_days: int = 10
    complaints_pause_all: int = Field(default=2, ge=1, le=2)
    # [CD] counsel sign-off reference that lets J1 dial a DND number on a transaction basis.
    dnd_j1_transaction_signoff_ref: str | None = None
    enabled_country_codes: frozenset[str] = frozenset({"+91"})
    # [CD] the DLT-declared CLI each journey dials from. Placeholders until registration.
    cli_by_purpose: dict[Literal["J1", "J2"], str] = Field(default_factory=_default_clis)
    clearance_ttl_seconds: int = Field(default=60, ge=1, le=60)


class HoldoutSettings(BaseModel):
    experiment_salt: str = "av-pilot-2026-11"
    percent: int = Field(default=10, ge=1, le=50)


class RetentionSettings(BaseModel):
    audio_days: int = 30
    transcript_days: int = 180
    # [CD] consent records as the law requires; kept until counsel confirms.
    consent_days: int | None = None
    ict_log_days: int = Field(default=180, ge=180)


class ResidencySettings(BaseModel):
    # [CD] Agoda's allowlist of provider regions.
    allowed_regions: frozenset[str] = frozenset({"in"})
    provider_regions: dict[str, str] = Field(default_factory=dict)


class GrievanceSettings(BaseModel):
    # [CD] Agoda's grievance channel. Placeholder is obviously not real.
    channel: str = "Agoda grievance officer: [CD: grievance contact]"
    notice_url: str = "https://example.invalid/agoda-voice/notice"


class ClientSettings(BaseModel):
    # The company this tenant calls on behalf of; spoken in every opening and template (D-035).
    name: str = "Agoda"


class PaymentLinkSettings(BaseModel):
    # [CD] link format and expiry.
    base_url: str = "https://example.invalid/agoda/pay"
    expiry_hours: int = 24


class OidcSettings(BaseModel):
    """Console SSO (brief v3 S7). Absent means SSO is not configured for this tenant."""

    issuer: str
    audience: str
    jwks_url: str
    role_claim: str = "groups"
    group_roles: dict[str, Literal["admin", "ops", "auditor", "read_only"]] = Field(
        default_factory=dict
    )
    leeway_seconds: int = 30


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AV_", env_nested_delimiter="__", extra="forbid", frozen=True
    )

    environment: Literal["dev", "test", "production"] = "dev"
    tenant_id: str = "agoda-in"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/agoda_voice"
    bus: BusName = "memory"
    kafka_bootstrap: str = "localhost:19092"
    phone_pepper: str = "dev-pepper-not-secret"
    # Calls a dispatcher runs at once (D-033). Gates stay sequential whatever the value.
    call_workers: int = Field(default=1, ge=1, le=200)
    api_tokens: dict[str, str] = Field(
        default_factory=lambda: {
            "dev-admin-token": "admin",
            "dev-ops-token": "ops",
            "dev-auditor-token": "auditor",
            "dev-ro-token": "read_only",
        }
    )

    stt: SttName = "mock"
    tts: TtsName = "mock"
    llm: LlmName = "mock"
    telephony: TelephonyName = "mock"
    whatsapp: WhatsAppName = "mock"
    crm: CrmName = "mock"
    voice_gender: Literal["female", "male"] = "female"
    voice_id: str = "mock-female-1"

    ntp_servers: tuple[str, ...] = ("samay1.nic.in", "samay2.nic.in")
    whatsapp_utility_rate_paise: Decimal = Decimal("11.50")
    gst_rate: Decimal = Decimal("0.18")

    oidc: OidcSettings | None = None
    compliance: ComplianceSettings = ComplianceSettings()
    holdout: HoldoutSettings = HoldoutSettings()
    retention: RetentionSettings = RetentionSettings()
    residency: ResidencySettings = ResidencySettings()
    grievance: GrievanceSettings = GrievanceSettings()
    payment_link: PaymentLinkSettings = PaymentLinkSettings()
    client: ClientSettings = ClientSettings()


_MOCK_ROLES = ("stt", "tts", "llm", "telephony", "whatsapp", "crm")


def validate_for_environment(settings: Settings) -> None:
    """Rejects configuration that is legal for tests but never for production."""
    if settings.environment != "production":
        return
    mocks = [role for role in _MOCK_ROLES if getattr(settings, role) == "mock"]
    if mocks:
        raise ProductionConfigError(f"mock providers are not allowed in production: {mocks}")
    if settings.bus == "memory":
        raise ProductionConfigError("memory bus is not allowed in production")
    if settings.database_url.startswith("sqlite"):
        raise ProductionConfigError("sqlite is not allowed in production")
    if settings.phone_pepper.startswith("dev-"):
        raise ProductionConfigError("phone_pepper must be set from the secret store")
    if settings.api_tokens:
        # Production authenticates with hashed API keys and SSO only; static tokens are dev-only.
        raise ProductionConfigError("static api_tokens are not allowed in production")
    allowed = settings.residency.allowed_regions
    for role in _MOCK_ROLES:
        region = settings.residency.provider_regions.get(role)
        if region is None:
            raise ProductionConfigError(f"provider region for {role} is not declared")
        if region not in allowed:
            raise ProductionConfigError(f"{role} region {region!r} is outside {sorted(allowed)}")
    if not settings.ntp_servers:
        raise ProductionConfigError("NTP servers must be configured (REQ-SEC-03)")
    # Every notice and WhatsApp template carries these; a placeholder must never reach a customer.
    for name, value in (
        ("grievance.channel", settings.grievance.channel),
        ("grievance.notice_url", settings.grievance.notice_url),
        ("payment_link.base_url", settings.payment_link.base_url),
    ):
        if "[CD" in value or "example.invalid" in value:
            raise ProductionConfigError(f"{name} is still a placeholder")
    if settings.stt == "sarvam":
        # Sarvam returns no per-utterance confidence, so the low-confidence safety rule (D-103)
        # would never fire. Calibrate a confidence source on real audio (M8) before enabling it.
        raise ProductionConfigError("stt=sarvam has no calibrated confidence yet (D-103, M8)")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    validate_for_environment(settings)
    return settings
