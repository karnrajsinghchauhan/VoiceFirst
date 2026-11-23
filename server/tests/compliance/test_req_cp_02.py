"""REQ-CP-01 / CP-02: no CCPA dark pattern in any prompt line, template or agent utterance;
the amount is stated once; no scarcity; a refused ask is never repeated."""

from app.voice.dark_patterns import find_nagging


def test_nagging_detector() -> None:
    assert find_nagging([("payment_link", True), ("payment_link", False)])
    assert not find_nagging([("payment_link", False), ("payment_link", False)])
