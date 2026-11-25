"""REQ-DPDP-08: consent_record carries consent_manager_id and artefact_ref for a future Consent Manager."""

import json
from pathlib import Path

from app.compliance.consent import record_consent

SCHEMA = json.loads(
    (Path(__file__).parents[3] / "contracts/schemas/consent_record.json").read_text()
)


def test_schema_requires_consent_manager_fields() -> None:
    for name in ("consent_manager_id", "artefact_ref"):
        assert name in SCHEMA["required"]
        assert "null" in SCHEMA["properties"][name]["type"]


def test_records_round_trip_the_fields(session, settings, clock) -> None:
    rec = record_consent(
        session,
        settings,
        phone_e164="+919812345678",
        basis="explicit",
        purpose="J1",
        channel="voice",
        obtained_at=clock.now(),
        booking_id=None,
        source_ref="call_1",
        trace_id="0" * 32,
    )
    dumped = rec.model_dump()
    assert dumped["consent_manager_id"] is None and dumped["artefact_ref"] is None
