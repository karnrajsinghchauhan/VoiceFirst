"""Row-level security statements. Every migration that creates a tenant table calls enable().

The policy text matches migration b2c3d4e5f6a7; tests/e2e/test_tenant_isolation checks that
every table in the models has forced RLS after `alembic upgrade head`.
"""

from __future__ import annotations

POLICY = "tenant_isolation"
_EXPR = "tenant_id = current_setting('app.tenant_id')"


def enable(table: str) -> list[str]:
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY {POLICY} ON {table} USING ({_EXPR}) WITH CHECK ({_EXPR})",
    ]


def disable(table: str) -> list[str]:
    return [
        f"DROP POLICY {POLICY} ON {table}",
        f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY",
    ]
