"""add_outbox_next_retry_at

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-18 00:00:00.000000

Adds outbox_events.next_retry_at to support exponential backoff for poison
events (BUG-5): failing rows are rescheduled rather than re-claimed on every
poll cycle, preventing head-of-line blocking of healthy events.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "outbox_events" not in inspector.get_table_names():
        return

    columns = {c["name"] for c in inspector.get_columns("outbox_events")}
    if "next_retry_at" not in columns:
        op.add_column(
            "outbox_events",
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            op.f("ix_outbox_events_next_retry_at"),
            "outbox_events",
            ["next_retry_at"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "outbox_events" not in inspector.get_table_names():
        return

    columns = {c["name"] for c in inspector.get_columns("outbox_events")}
    if "next_retry_at" in columns:
        op.drop_index(op.f("ix_outbox_events_next_retry_at"), table_name="outbox_events")
        op.drop_column("outbox_events", "next_retry_at")
