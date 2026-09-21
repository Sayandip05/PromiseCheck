"""Audit module database model for append-only compliance logs."""

import uuid

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class AuditEvent(Base, TenantMixin):
    """Append-only operational and security audit log entry."""

    __tablename__ = "audit_events"

    # Composite index: paginated audit log queries always filter by workspace
    # and sort by recency.  A single index covers both.
    __table_args__ = (
        Index("ix_audit_events_ws_created", "workspace_id", "created_at"),
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # description: human-readable summary as a first-class indexed column so audit
    # queries ("find events where description contains X") use a B-tree text scan
    # instead of JSONB path operators.
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
