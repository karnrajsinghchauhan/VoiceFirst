"""Alembic migrations build the same schema as the models (no autogenerate drift) on Postgres."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.db import Base, make_engine

pytestmark = pytest.mark.e2e
SERVER = Path(__file__).parents[2]


def _alembic(*args: str, url: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "AV_DATABASE_URL": url}
    return subprocess.run(
        ["alembic", *args], cwd=SERVER, env=env, capture_output=True, text=True, check=False
    )


def test_upgrade_then_check_has_no_drift() -> None:
    url = os.environ["AV_TEST_DATABASE_URL"]
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    up = _alembic("upgrade", "head", url=url)
    assert up.returncode == 0, up.stderr
    check = _alembic("check", url=url)
    assert check.returncode == 0, check.stdout + check.stderr
    down = _alembic("downgrade", "base", url=url)
    assert down.returncode == 0, down.stderr
    engine.dispose()
