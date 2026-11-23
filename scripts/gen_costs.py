"""`make costs`: regenerates docs/unit-economics.md and the proposal's cost table from config/costs.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import Settings
from app.costs.book import load_book
from app.costs.render import cost_table, replace_between_markers, unit_economics_doc

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    book = load_book(Settings(environment="test").costs_file)
    (ROOT / "docs/unit-economics.md").write_text(unit_economics_doc(book))
    proposal = ROOT / "docs/proposal-draft.md"
    proposal.write_text(replace_between_markers(proposal.read_text(), cost_table(book)))
    sys.stdout.write("costs: regenerated docs/unit-economics.md and docs/proposal-draft.md\n")


if __name__ == "__main__":
    main()
