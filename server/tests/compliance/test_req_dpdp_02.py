"""REQ-DPDP-01 (itemised notice), -02 (purpose tags), -04 (child on the line)."""

import json

import pytest

from app.core.errors import PurposeFieldViolationError
from app.voice import context


def test_every_contract_field_is_purpose_tagged() -> None:
    tags = context.field_purposes()
    assert "amount_due" in tags and tags["amount_due"] == {"J1"}
    assert "stay.guests" in tags and tags["stay.guests"] == {"J2"}


def test_untagged_field_fails(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    schema = json.loads(context.SCHEMA_PATH.read_text())
    schema["properties"]["new_field"] = {"type": "string"}
    path = tmp_path / "booking_event.json"
    path.write_text(json.dumps(schema))
    monkeypatch.setattr(context, "SCHEMA_PATH", path)
    context.field_purposes.cache_clear()
    try:
        with pytest.raises(PurposeFieldViolationError):
            context.field_purposes()
    finally:
        context.field_purposes.cache_clear()
