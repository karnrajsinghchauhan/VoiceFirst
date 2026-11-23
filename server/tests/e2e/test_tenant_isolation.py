"""S7 DONE: tenant isolation is enforced by Postgres row-level security, not by query filters.

Runs as a non-superuser role (superusers bypass RLS). Tenant B can neither read nor write
tenant A's rows, and a connection that never declared a tenant cannot read anything.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

import app.models  # noqa: F401
from app.compliance.models import KillSwitchRow
from app.core.db import Base, make_engine, make_session_factory, transaction

pytestmark = pytest.mark.e2e
SERVER = Path(__file__).parents[2]
ROLE, PASSWORD = "av_app_isolation", "isolation-test-only"


def _as_role(url: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.split("@")[-1]
    return urlunsplit(parts._replace(netloc=f"{ROLE}:{PASSWORD}@{host}"))


@pytest.fixture(scope="module")
def app_url():
    admin_url = os.environ["AV_TEST_DATABASE_URL"]
    admin = make_engine(admin_url, "agoda-in")
    Base.metadata.drop_all(admin)
    with admin.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    env = {**os.environ, "AV_DATABASE_URL": admin_url}
    up = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=SERVER,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert up.returncode == 0, up.stderr
    with admin.begin() as conn:
        conn.execute(text(f"DROP OWNED BY {ROLE}") if _role_exists(conn) else text("SELECT 1"))
        conn.execute(text(f"DROP ROLE IF EXISTS {ROLE}"))
        conn.execute(text(f"CREATE ROLE {ROLE} LOGIN PASSWORD '{PASSWORD}'"))
        conn.execute(
            text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}")
        )
    yield _as_role(admin_url)
    with admin.begin() as conn:
        conn.execute(text(f"DROP OWNED BY {ROLE}"))
        conn.execute(text(f"DROP ROLE {ROLE}"))
    admin.dispose()


def _role_exists(conn) -> bool:  # type: ignore[no-untyped-def]
    return bool(
        conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": ROLE}).scalar()
    )


def _row(tenant: str) -> KillSwitchRow:
    return KillSwitchRow(
        tenant_id=tenant,
        engaged=True,
        actor="ops",
        reason="isolation test",
        changed_at=datetime(2026, 11, 23, tzinfo=UTC),
    )


def test_every_table_has_row_level_security(app_url):
    with psycopg.connect(os.environ["AV_TEST_DATABASE_URL"].replace("+psycopg", "")) as conn:
        rows = conn.execute(
            "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'"
        ).fetchall()
    tables = {name: (rls, force) for name, rls, force in rows if name != "alembic_version"}
    assert set(tables) == set(Base.metadata.tables)
    assert [n for n, flags in tables.items() if flags != (True, True)] == []


def test_cross_tenant_read_and_write_fail(app_url):
    a = make_session_factory(make_engine(app_url, "tenant-a"))
    b = make_session_factory(make_engine(app_url, "tenant-b"))
    with transaction(a) as s:
        s.add(_row("tenant-a"))
    with transaction(b) as s:
        assert s.scalars(select(KillSwitchRow)).all() == []
        assert s.get(KillSwitchRow, "tenant-a") is None
    with pytest.raises(ProgrammingError, match="row-level security"), transaction(b) as s:
        s.add(_row("tenant-a"))
    with transaction(a) as s:
        assert [r.tenant_id for r in s.scalars(select(KillSwitchRow))] == ["tenant-a"]


def test_connection_without_a_tenant_reads_nothing(app_url):
    with psycopg.connect(app_url.replace("+psycopg", "")) as conn, pytest.raises(psycopg.Error):
        conn.execute("SELECT * FROM kill_switch").fetchall()


def test_superuser_connection_is_refused_in_production():
    from app.core.db import assert_not_superuser
    from app.core.errors import ProductionConfigError

    with pytest.raises(ProductionConfigError):
        assert_not_superuser(make_engine(os.environ["AV_TEST_DATABASE_URL"], "agoda-in"))


def test_app_role_passes_the_superuser_check(app_url):
    from app.core.db import assert_not_superuser

    assert_not_superuser(make_engine(app_url, "tenant-a"))
