"""S4 DONE: a seeded week of synthetic calls -> weekly review with clustered causes and three
draft fix PRs, each with a persona that reproduces the failure on today's agent."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.core.db import transaction
from app.costs.book import load_book
from app.postcall.crypto import DataCipher
from app.postcall.settings import PostcallSettings
from app.qa.nightly import score_unscored
from app.qa.weekly import build_review, draft_fixes, load_week, write_review
from app.simulator.assertions import check_run, task_pass
from app.simulator.caller import load_persona
from app.simulator.scenario import run_text
from app.simulator.week import seed_week

WEEK = date(2026, 11, 16)
PROMPTS = Path(__file__).parents[2] / "app/voice/prompts"


def _prompt_digest() -> str:
    h = hashlib.sha256()
    for p in sorted(PROMPTS.rglob("*")):
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


@pytest.fixture(scope="module")
def week(tmp_path_factory):
    from app.core.bus import MemoryBus
    from app.core.db import create_all, make_engine, make_session_factory
    from tests.factories import make_settings

    settings = make_settings()
    engine = make_engine("sqlite://")
    create_all(engine)
    factory = make_session_factory(engine)
    cipher = DataCipher(PostcallSettings().data_key)
    before = _prompt_digest()
    seeded = seed_week(factory, MemoryBus(), settings, cipher, WEEK, calls_per_day=21)
    with transaction(factory) as s:
        scored = score_unscored(
            s,
            cipher,
            load_book(settings.costs_file),
            settings.tenant_id,
            datetime(2026, 11, 23, tzinfo=UTC),
        )
        records = load_week(s, cipher, WEEK)
    review = build_review(records, WEEK)
    root = tmp_path_factory.mktemp("repo")
    review_path = write_review(review, root)
    drafts = draft_fixes(review, records, root)
    return {
        "settings": settings,
        "seeded": seeded,
        "scored": scored,
        "records": records,
        "review": review,
        "review_path": review_path,
        "drafts": drafts,
        "root": root,
        "prompts_before": before,
    }


def test_every_call_is_scored(week):
    assert week["seeded"] == week["scored"] == len(week["records"]) == 147


def test_review_clusters_causes(week):
    causes = [s.cause for s in week["review"].top]
    assert {"missed_opt_out", "customer_confusion", "wrong_language"} <= set(causes)
    assert len(causes) <= 5
    text = week["review_path"].read_text()
    assert "Example calls: syn-" in text and "Proposed fix:" in text
    assert "+91" not in text  # transcripts are redacted; numbers never land in the review


def test_three_draft_fixes_each_reproduce_their_failure(week):
    drafts = week["drafts"]
    assert len(drafts) == 3
    for d in drafts:
        assert d.persona_path.parent.name == "proposed"
        assert d.branch.startswith("fix/qa-2026-11-16-")
        pr = d.pr_path.read_text()
        assert "Not applied" in pr and "named human" in pr
        persona = load_persona(d.persona_path)
        run = run_text(week["settings"], persona, persona.languages[0], 0)
        # A reproduction fails its expectation on the current agent; the fix makes it pass.
        assert not task_pass(check_run(run)), f"{d.persona_path.name} does not reproduce"


def test_the_loop_never_edits_production_prompts(week):
    assert _prompt_digest() == week["prompts_before"]
    qa_sources = "".join(p.read_text() for p in (Path(__file__).parents[2] / "app/qa").glob("*.py"))
    assert "voice/prompts" not in qa_sources.replace("Nothing here writes to voice/prompts", "")
