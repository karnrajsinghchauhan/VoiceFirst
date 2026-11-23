"""REQ-TRAI-10: complaint ingest accepts DLT-forwarded complaints, including call-management-app reports."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.compliance.complaints import ingest_complaint
from app.contracts.generated.complaint import Complaint
from tests.factories import SERVICE_CLI, seed_cli

SCHEMA = json.loads((Path(__file__).parents[3] / "contracts/schemas/complaint.json").read_text())


def _payload(source: str) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "tenant_id": "agoda-in",
        "trace_id": "0" * 32,
        "complaint_id": "cmp_1",
        "cli_e164": SERVICE_CLI,
        "complainant_hash": "a" * 64,
        "received_at": "2026-11-23T06:30:00Z",
        "source": source,
        "ai_flagged": True,
        "dlt_ref": "DLT-CMP-77",
    }


def test_schema_accepts_both_dlt_sources() -> None:
    assert {"dlt_forwarded", "call_management_app_via_dlt"} <= set(
        SCHEMA["properties"]["source"]["enum"]
    )


@pytest.mark.parametrize("source", ["dlt_forwarded", "call_management_app_via_dlt"])
def test_ingest_contract(session, settings, bus, source: str) -> None:
    seed_cli(session, settings)
    complaint = Complaint.model_validate(_payload(source))
    out = ingest_complaint(session, bus, settings, complaint)
    assert out.cli_paused
    assert bus.messages["av.complaints.v1"][0][1]["source"] == source


def test_unknown_fields_rejected_at_the_edge() -> None:
    bad = _payload("dlt_forwarded") | {"raw_phone": "+919812345678"}
    with pytest.raises(ValidationError):
        Complaint.model_validate(bad)
