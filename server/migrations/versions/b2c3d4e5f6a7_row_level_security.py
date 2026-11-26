"""Row-level security on every tenant table (brief v3 S7).

Policy: a row is visible and writable only when its tenant_id equals the connection's
`app.tenant_id`. current_setting() without missing_ok raises when the setting is absent,
so a connection that never declared its tenant fails loudly instead of seeing every row.
FORCE applies the policy to the table owner too; superusers still bypass RLS, which is why
the application connects as the non-superuser role described in docs/configuration.md.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The tenant tables at this revision. Later migrations that add a table enable RLS on it.
TENANT_TABLES = (
    "audio_refs", "audit_log", "booking_events", "call_outcomes", "callbacks",
    "campaign_pauses", "campaign_state", "clearances", "cli_registry", "complaints",
    "consent_records", "dial_attempts", "dial_queue", "gate_decisions", "handoffs",
    "holdout_members", "incidents", "kill_switch", "opt_outs", "preference_registry",
    "rights_requests", "transcripts", "whatsapp_inbound", "whatsapp_sends", "whatsapp_state",
)
_POLICY = "tenant_isolation"
_EXPR = "tenant_id = current_setting('app.tenant_id')"


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {_POLICY} ON {table} USING ({_EXPR}) WITH CHECK ({_EXPR})")


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY {_POLICY} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
