"""REQ-DPDP-01 (itemised notice), -02 (purpose tags), -04 (child on the line)."""

from dataclasses import asdict

import pytest

from app.voice.notice import build_notice
from tests.voice.helpers import settings as av_settings


@pytest.mark.parametrize("purpose", ["J1", "J2"])
def test_notice_has_every_required_item(purpose: str) -> None:
    notice = asdict(build_notice(av_settings(), purpose))  # type: ignore[arg-type]
    assert set(notice) == {
        "purpose",
        "data_items",
        "recording",
        "ai_disclosure",
        "rights",
        "how_to_withdraw",
        "grievance_contact",
        "board_complaint",
        "retention",
        "url",
    }
    assert notice["data_items"] and all(notice.values())
    assert any("erase" in r for r in notice["rights"]) and any(
        "withdraw" in r for r in notice["rights"]
    )
    assert "Data Protection Board" in notice["board_complaint"]
    assert "call mat karo" in notice["how_to_withdraw"]


def test_notice_snapshot_j1() -> None:
    notice = build_notice(av_settings(), "J1")
    assert notice.purpose.startswith("Helping you complete the pending payment")
    assert notice.data_items == (
        "your first name",
        "your phone number",
        "the city of your booking",
        "the amount due and payment due date",
        "the call recording and a redacted transcript",
    )
