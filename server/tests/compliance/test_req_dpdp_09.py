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
    )
    base.update(overrides)
    return make_settings(**base)


def test_valid_production_config_passes() -> None:
    validate_for_environment(_prod())


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
