"""tenant_id on every table; phone-keyed tables keyed by (tenant_id, phone_hash).

Revision ID: a1b2c3d4e5f6
Revises: 3352282f8f92
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "3352282f8f92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Existing rows belong to the pilot tenant; the default is dropped straight after backfill.
_BACKFILL = "agoda-in"
_ADD = ("audio_refs", "callbacks", "dial_attempts", "transcripts", "whatsapp_sends")
_REKEY = ("opt_outs", "preference_registry", "whatsapp_inbound")


def upgrade() -> None:
    for table in _ADD + _REKEY:
        op.add_column(table, sa.Column("tenant_id", sa.String(), nullable=False,
                                       server_default=_BACKFILL))
        op.alter_column(table, "tenant_id", server_default=None)
    for table in _ADD:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
    for table in _REKEY:
        op.drop_constraint(f"{table}_pkey", table, type_="primary")
        op.create_primary_key(f"{table}_pkey", table, ["tenant_id", "phone_hash"])


def downgrade() -> None:
    for table in _REKEY:
        op.drop_constraint(f"{table}_pkey", table, type_="primary")
        op.create_primary_key(f"{table}_pkey", table, ["phone_hash"])
    for table in _ADD:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
    for table in _ADD + _REKEY:
        op.drop_column(table, "tenant_id")
