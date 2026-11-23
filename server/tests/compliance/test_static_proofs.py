"""11.4 static proofs: import boundary, clearance construction sites, no card fields in contracts."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

SERVER = Path(__file__).parents[2]
APP = SERVER / "app"
CONTRACTS = SERVER.parent / "contracts"

CARD_FIELD = re.compile(
    r"(card|pan_?number|cvv|cvc|expiry|exp_month|exp_year|upi_?pin|otp|"
    r"netbanking|password|card_number)",
    re.IGNORECASE,
)


def _py_files() -> list[Path]:
    return [p for p in APP.rglob("*.py") if "generated" not in p.parts]


def test_import_linter_contract_holds() -> None:
    result = subprocess.run(
        ["lint-imports"], cwd=SERVER, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Only the dispatcher may import telephony.dial KEPT" in result.stdout


def test_only_dispatcher_imports_dial_anywhere_in_app() -> None:
    offenders = []
    for path in _py_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.telephony.dial":
                rel = path.relative_to(APP).as_posix()
                if rel != "campaigns/dispatcher.py":
                    offenders.append(rel)
    assert offenders == []


def test_clearance_minted_only_in_compliance() -> None:
    offenders = []
    for path in _py_files():
        rel = path.relative_to(APP).as_posix()
        if rel.startswith("compliance/"):
            continue
        source = path.read_text()
        if re.search(r"\bmint\(|GateClearance\(|_MINT\b", source):
            offenders.append(rel)
    assert offenders == []


def test_mint_called_only_from_evaluate() -> None:
    callers = []
    for path in (APP / "compliance").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "mint":
                callers.append(path.name)
    assert callers == ["evaluate.py"]


def _property_names(node: object) -> list[str]:
    names: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                names.extend(value.keys())
            names.extend(_property_names(value))
    elif isinstance(node, list):
        for item in node:
            names.extend(_property_names(item))
    return names


def test_no_card_fields_in_any_contract() -> None:
    names = []
    for schema in (CONTRACTS / "schemas").glob("*.json"):
        names.extend(_property_names(json.loads(schema.read_text())))
    assert names, "no properties found; the walker is broken"
    assert [n for n in names if CARD_FIELD.search(n)] == []


def test_no_card_columns_in_any_table() -> None:
    import app.models  # noqa: F401
    from app.core.db import Base

    columns = [c.name for t in Base.metadata.tables.values() for c in t.columns]
    assert [c for c in columns if CARD_FIELD.search(c)] == []


def test_dial_has_no_cli_parameter() -> None:
    """REQ-CLI-01: the CLI comes only from the clearance; no caller can pass another."""
    import inspect

    from app.telephony.dial import dial

    assert "cli" not in " ".join(inspect.signature(dial).parameters)
