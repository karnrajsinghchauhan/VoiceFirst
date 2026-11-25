"""REQ-SEC-01: the control list lives in SECURITY.md."""

from pathlib import Path

DOC = (Path(__file__).parents[3] / "SECURITY.md").read_text()


def test_controls_cover_the_baseline() -> None:
    for needle in (
        "Audit log",
        "RBAC",
        "Encryption in transit",
        "Encryption at rest",
        "No training on client data",
        "Processing record",
        "CERT-In",
        "180 days",
    ):
        assert needle in DOC


def test_disclaimer_present() -> None:
    assert "not affiliated with or endorsed by Agoda" in DOC
