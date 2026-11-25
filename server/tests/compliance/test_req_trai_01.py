"""REQ-TRAI-01: every outbound call is A2P; the CLI must carry a declaration recorded on DLT."""

from datetime import UTC, datetime

import pytest

from app.compliance.gates import gate_cli_declared
from app.core.errors import CliNotDeclaredError
from tests.compliance.helpers import make_ctx, service_cli


def test_declared_cli_passes() -> None:
    gate_cli_declared(make_ctx())


@pytest.mark.parametrize(
    "overrides",
    [
        {"a2p_declared": False},
        {"declaration_ref": None},
        {"declaration_ref": ""},
        {"dlt_recorded_at": None},
        {"oap": ""},
    ],
)
def test_cli_without_declaration_raises(overrides: dict[str, object]) -> None:
    with pytest.raises(CliNotDeclaredError):
        gate_cli_declared(make_ctx(cli=service_cli(**overrides)))


def test_unregistered_cli_raises() -> None:
    with pytest.raises(CliNotDeclaredError):
        gate_cli_declared(make_ctx(cli=None))


def test_declaration_timestamp_is_aware() -> None:
    assert service_cli().dlt_recorded_at == datetime(2026, 10, 1, tzinfo=UTC)
