"""REQ-CLI-01: only the declared CLI is ever shown; no code path can spoof a CLI."""

import inspect

import pytest

from app.compliance.evaluate import evaluate
from app.core.errors import CliNotDeclaredError
from app.providers.telephony.mock import MockTelephony
from app.telephony import dial as dial_module
from tests.factories import SERVICE_CLI, make_event, seed_cli, seed_consent


def test_shown_cli_is_the_cleared_cli(session, settings, clock, bus) -> None:
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    clearance = evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)
    tel = MockTelephony()
    dial_module.dial(session, clearance, tel, clock, settings.tenant_id, settings.phone_pepper)
    assert tel.placed[0][1] == SERVICE_CLI


def test_unregistered_cli_cannot_be_cleared(session, settings, clock, bus) -> None:
    event = make_event(settings)
    seed_cli(session, settings)
    seed_consent(session, settings, event)
    with pytest.raises(CliNotDeclaredError):
        evaluate(session, bus, settings, clock, event, "J1", "+911600999999")


def test_place_call_is_called_only_with_the_clearance_cli() -> None:
    source = inspect.getsource(dial_module.dial)
    assert "provider.place_call(clearance.phone_e164, clearance.cli_e164" in source
