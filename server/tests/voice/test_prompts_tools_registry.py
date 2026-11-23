import pytest

from app.core.errors import PromptLintError, ProviderNotBuiltError, ToolNotAllowedError
from app.providers.registry import build_providers
from app.voice.prompts import PROMPT_VERSION, lines, placeholders, render
from app.voice.tools import ALLOWED_TOOLS, check_allowed
from tests.voice.helpers import settings

_VALUES = {
    k: "x"
    for k in (
        "first_name",
        "city",
        "property_name",
        "check_in_date",
        "check_out_date",
        "guests",
        "amount",
        "due_date",
        "booking_tail",
    )
}


def test_every_line_renders_in_every_language() -> None:
    for act, variants in lines().items():
        for lang in variants:
            assert render(act, lang, _VALUES)  # type: ignore[arg-type]


def test_languages_use_the_same_placeholders() -> None:
    for act, variants in lines().items():
        assert len({frozenset(placeholders(t)) for t in variants.values()}) == 1, act


def test_missing_placeholder_raises() -> None:
    with pytest.raises(PromptLintError):
        render("j1_opening", "hinglish", {})


def test_changelog_mentions_current_version() -> None:
    from pathlib import Path

    import app.voice.prompts as p

    assert PROMPT_VERSION in (Path(p.__file__).parent / "CHANGELOG.md").read_text()


def test_allowlist_has_no_money_tool() -> None:
    money = {"refund", "cancel", "reprice", "agoda_cash", "waive", "discount"}
    assert not any(m in name for name in ALLOWED_TOOLS for m in money)
    assert len(ALLOWED_TOOLS) == 10


@pytest.mark.parametrize(
    "name", ["issue_refund", "cancel_booking", "apply_discount", "issue_agoda_cash"]
)
def test_money_tools_rejected(name: str) -> None:
    with pytest.raises(ToolNotAllowedError):
        check_allowed(name)


def test_registry_builds_one_mock_per_role() -> None:
    providers = build_providers(settings())
    assert {providers.stt.name, providers.tts.name, providers.llm.name} == {"mock"}


@pytest.mark.parametrize(
    "role,name",
    [
        ("stt", "selfhosted"),
        ("tts", "elevenlabs"),
        ("llm", "vllm"),
        ("crm", "hubspot"),
    ],
)
def test_unbuilt_provider_fails_at_boot(role: str, name: str) -> None:
    with pytest.raises(ProviderNotBuiltError):
        build_providers(settings().model_copy(update={role: name}))


def test_real_provider_without_key_fails_at_boot(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.errors import ConfigError

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        build_providers(settings().model_copy(update={"llm": "openai"}))


def test_livekit_turn_handling_is_pinned() -> None:
    from app.voice.livekit_worker import LIVEKIT_AGENTS_VERSION, turn_handling

    opts = turn_handling("vad")
    assert opts["interruption"]["mode"] == "adaptive"
    assert opts["endpointing"]["mode"] == "fixed"
    assert opts["preemptive_generation"]["enabled"] is True
    import importlib.metadata

    assert importlib.metadata.version("livekit-agents") == LIVEKIT_AGENTS_VERSION


@pytest.mark.parametrize(
    ("role", "name"),
    [("telephony", "plivo"), ("telephony", "exotel"), ("whatsapp", "meta_cloud_api")],
)
def test_real_channel_without_keys_fails_at_boot(
    role: str, name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.errors import ConfigError

    for var in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "AV_META_ACCESS_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ConfigError):
        build_providers(settings().model_copy(update={role: name}))
