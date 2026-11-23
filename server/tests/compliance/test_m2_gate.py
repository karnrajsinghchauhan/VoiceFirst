"""M2 gate: every REQ listed in docs/compliance.md has a passing test file."""

from pathlib import Path

DOC = (Path(__file__).parents[3] / "docs/compliance.md").read_text()


def test_every_req_in_the_doc_has_a_test_file() -> None:
    import re

    reqs = sorted(set(re.findall(r"REQ-[A-Z]+-\d{2}", DOC)))
    here = Path(__file__).parent
    missing = [r for r in reqs if not (here / f"test_{r.lower().replace('-', '_')}.py").exists()]
    assert missing == [], f"REQs without a test file: {missing}"
