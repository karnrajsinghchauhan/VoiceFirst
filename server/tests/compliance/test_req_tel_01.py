"""REQ-TEL-01: TCCCPR is the operative rulebook; the Act's section refs are recorded as [CD] for counsel."""

from pathlib import Path

DOC = (Path(__file__).parents[3] / "docs/compliance.md").read_text()


def test_compliance_doc_records_the_act_and_counsel_cd() -> None:
    section = DOC.split("## Telecommunications Act 2023", 1)[1].split("##", 1)[0]
    assert "REQ-TEL-01" in section and "[CD" in section and "No separate code path" in section


def test_compliance_doc_is_marked_not_legal_advice() -> None:
    assert "not legal advice" in DOC and "sign it off before go-live" in DOC
