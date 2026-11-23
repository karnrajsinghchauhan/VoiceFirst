"""S6: one unit-price change in config/costs.yaml moves every cost view."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.stubs import build_stub_deps
from app.core.errors import ConfigError
from app.costs.book import load_book
from app.costs.render import cost_table, unit_economics_doc
from app.messaging.whatsapp import template_cost_paise
from app.simulator.caller import load_personas
from app.simulator.scenario import run_text
from tests.factories import make_settings

ROOT = Path(__file__).parents[3]
DEFAULT = ROOT / "config/costs.yaml"


def _with_price(tmp_path: Path, name: str, price: str) -> str:
    data = yaml.safe_load(DEFAULT.read_text())
    for c in data["components"]:
        if c["name"] == name:
            c["unit_price"] = price
    out = tmp_path / "costs.yaml"
    out.write_text(yaml.safe_dump(data))
    return str(out)


def _costs(settings, session_factory, bus, clock) -> dict:
    app = create_app(build_stub_deps(settings, session_factory, bus, clock))
    r = TestClient(app).get("/costs", headers={"Authorization": "Bearer dev-ro-token"})
    assert r.status_code == 200, r.text
    return r.json()


def test_one_price_change_moves_every_view(tmp_path, session_factory, bus, clock):
    base = make_settings()
    changed = make_settings(costs_file=_with_price(tmp_path, "stt", "4.90"))
    before, after = (
        _costs(base, session_factory, bus, clock),
        _costs(changed, session_factory, bus, clock),
    )
    stt_before = next(c for c in before["components"] if c["name"] == "stt")
    stt_after = next(c for c in after["components"] if c["name"] == "stt")
    assert Decimal(stt_after["per_minute_paise"]) == Decimal(stt_before["per_minute_paise"]) * 10
    assert Decimal(after["per_resolved_contact_paise"]) > Decimal(
        before["per_resolved_contact_paise"]
    )
    # The agent's per-call cost record reads the same book.
    persona = next(p for p in load_personas() if p.id == "C-01")
    stt_cost = [
        run_text(s, persona, "hinglish", 0).result.outcome.cost.stt for s in (base, changed)
    ]
    assert stt_cost[1] > stt_cost[0]
    # The generated documents follow.
    b0, b1 = load_book(base.costs_file), load_book(changed.costs_file)
    assert cost_table(b0) != cost_table(b1) and "| stt | per minute | 4.90 |" in cost_table(b1)


def test_whatsapp_price_change_moves_template_cost(tmp_path):
    changed = make_settings(costs_file=_with_price(tmp_path, "whatsapp", "0.8631"))
    assert template_cost_paise(make_settings()) == 14
    assert template_cost_paise(changed) == 102  # 86.31 paise + 18% GST, rounded up


def test_committed_documents_match_the_book():
    book = load_book(make_settings().costs_file)
    assert (ROOT / "docs/unit-economics.md").read_text() == unit_economics_doc(book)
    assert cost_table(book) in (ROOT / "docs/proposal-draft.md").read_text()


def test_every_price_is_sourced_or_an_estimate():
    book = load_book(make_settings().costs_file)
    for c in book.components:
        assert c.estimate or (c.source_url and c.checked_at)
    assert book.re_check_before_quoting


def test_non_estimate_without_source_is_rejected(tmp_path):
    data = yaml.safe_load(DEFAULT.read_text())
    data["components"][2]["source_url"] = None  # stt, not an estimate
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(data))
    with pytest.raises(ConfigError):
        load_book(str(bad))
