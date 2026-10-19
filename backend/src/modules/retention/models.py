"""Retention and deletion-job database model (FR-20 / NFR-13).

Deletion is asynchronous and auditable: a job records exactly what was removed,
when, by whom, and the tombstone hash so downstream artifacts (embeddings,
backups, access records) can be cascaded and verified.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class DeletionJob(Base, TenantMixin):
    """Tracks a tenant data-deletion request through its lifecycle."""

    __tablename__ = "deletion_jobs"
    __table_args__ = (Index("ix_deletion_jobs_ws_status", "workspace_id", "status"),)

    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, running, completed, failed
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    tombstone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
