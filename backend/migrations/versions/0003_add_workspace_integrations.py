"""add_workspace_integrations

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-02 00:00:00.000000

Adds workspace_integrations table for Factor VI stateless connector persistence.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status_text", sa.String(255), nullable=False, server_default="Not connected"),
        sa.Column("last_sync", sa.String(100), nullable=False, server_default="Never"),
        sa.Column("channel_or_scope", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_integrations_id"), "workspace_integrations", ["id"], unique=False)
    op.create_index(op.f("ix_workspace_integrations_workspace_id"), "workspace_integrations", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_workspace_integrations_provider"), "workspace_integrations", ["provider"], unique=False)
    op.create_index(
        "ix_workspace_integrations_ws_provider",
        "workspace_integrations",
        ["workspace_id", "provider"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_integrations_ws_provider", table_name="workspace_integrations")
    op.drop_index(op.f("ix_workspace_integrations_provider"), table_name="workspace_integrations")
    op.drop_index(op.f("ix_workspace_integrations_workspace_id"), table_name="workspace_integrations")
    op.drop_index(op.f("ix_workspace_integrations_id"), table_name="workspace_integrations")
    op.drop_table("workspace_integrations")
