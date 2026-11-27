"""REQ-DPDP-09: India residency by default; production validator rejects other regions and mocks."""

from pathlib import Path

import pytest

from app.core.config import validate_for_environment
from app.core.errors import ProductionConfigError
from tests.factories import make_settings

ROLES = ("stt", "tts", "llm", "telephony", "whatsapp", "crm")


def _prod(**overrides):
    base = dict(
        environment="production",
        database_url="postgresql+psycopg://u:p@db/av",
        bus="kafka",
        phone_pepper="from-secret-store",
        api_tokens={},
        stt="sarvam",
        tts="sarvam_bulbul",
        llm="openai",
        telephony="plivo",
        whatsapp="meta_cloud_api",
        crm="zendesk",
        residency={"allowed_regions": ["in"], "provider_regions": dict.fromkeys(ROLES, "in")},
        grievance={
            "channel": "Grievance officer: grievance@agoda.example",
            "notice_url": "https://notice.agoda.example/voice",
        },
        payment_link={"base_url": "https://pay.agoda.example/link", "expiry_hours": 24},
    )
    base.update(overrides)
    return make_settings(**base)


def test_valid_production_config_fails_only_on_uncalibrated_stt() -> None:
    # Review R3: Sarvam returns no confidence, so D-103 would never fire; it stays off until M8.
    with pytest.raises(ProductionConfigError, match="no calibrated confidence"):
        validate_for_environment(_prod())


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "grievance": {
                "channel": "Agoda grievance officer: [CD: grievance contact]",
                "notice_url": "https://n.example/x",
            }
        },
        {
            "grievance": {
                "channel": "Officer: a@b.example",
                "notice_url": "https://example.invalid/agoda-voice/notice",
            }
        },
        {"payment_link": {"base_url": "https://example.invalid/agoda/pay", "expiry_hours": 24}},
    ],
)
def test_placeholder_customer_facing_values_rejected(overrides) -> None:
    # Review R2 H4: a placeholder grievance contact must never reach a customer.
    with pytest.raises(ProductionConfigError, match="placeholder"):
        validate_for_environment(_prod(**overrides))


def test_default_residency_is_india() -> None:
    assert make_settings().residency.allowed_regions == frozenset({"in"})


@pytest.mark.parametrize("role", ROLES)
def test_out_of_india_region_rejected(role: str) -> None:
    regions = dict.fromkeys(ROLES, "in") | {role: "us"}
    with pytest.raises(ProductionConfigError):
        validate_for_environment(
            _prod(residency={"allowed_regions": ["in"], "provider_regions": regions})
        )


@pytest.mark.parametrize("role", ROLES)
def test_undeclared_region_rejected(role: str) -> None:
    regions = {r: "in" for r in ROLES if r != role}
    with pytest.raises(ProductionConfigError):
        validate_for_environment(
            _prod(residency={"allowed_regions": ["in"], "provider_regions": regions})
        )


@pytest.mark.parametrize("role", ROLES)
def test_mock_rejected_in_production(role: str) -> None:
    with pytest.raises(ProductionConfigError):
        validate_for_environment(_prod(**{role: "mock"}))


@pytest.mark.parametrize(
    "overrides",
    [
        {"bus": "memory"},
        {"database_url": "sqlite://"},
        {"phone_pepper": "dev-pepper"},
        {"api_tokens": {"dev-admin-token": "admin"}},
    ],
)
def test_dev_infrastructure_rejected(overrides) -> None:
    with pytest.raises(ProductionConfigError):
        validate_for_environment(_prod(**overrides))


def test_subprocessors_document_lists_every_role() -> None:
    text = (Path(__file__).parents[3] / "docs/subprocessors.md").read_text().lower()
    for role in ROLES:
        assert role in text
