"""`make weekly-review`: score unscored calls, then write docs/weekly-review/<week>.md and draft fixes.

With --synthetic, first seeds a synthetic week into a throwaway database (the S4 demo);
otherwise reads the configured database.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.core.bus import MemoryBus
from app.core.config import Settings, get_settings
from app.core.db import create_all, make_engine, make_session_factory, transaction
from app.costs.book import load_book
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.qa.nightly import score_unscored
from app.qa.weekly import build_review, draft_fixes, load_week, write_review
from app.simulator.week import seed_week

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--week",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=date.today().weekday() + 7),
    )
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    cipher = DataCipher(PostcallSettings().data_key)
    if args.synthetic:
        settings = Settings(environment="test", database_url="sqlite://")
        engine = make_engine("sqlite://")
        create_all(engine)
        factory = make_session_factory(engine)
        seed_week(factory, MemoryBus(), settings, cipher, args.week, calls_per_day=21)
    else:
        settings = get_settings()
        factory = make_session_factory(make_engine(settings.database_url))
    with transaction(factory) as s:
        score_unscored(
            s, cipher, load_book(settings.costs_file), settings.tenant_id, datetime.now(UTC)
        )
        records = load_week(s, cipher, args.week)
    review = build_review(records, args.week)
    path = write_review(review, ROOT)
    drafts = draft_fixes(review, records, ROOT)
    sys.stdout.write(f"review: {path}\n")
    for d in drafts:
        sys.stdout.write(f"draft: {d.branch} persona={d.persona_path} pr={d.pr_path}\n")


if __name__ == "__main__":
    main()
