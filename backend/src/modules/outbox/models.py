"""Outbox module database model for durable transactional event dispatch."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class OutboxEvent(Base, TenantMixin):
    """Append-only transactional outbox record for durable Celery and Pub/Sub dispatch."""

    __tablename__ = "outbox_events"

    __table_args__ = (
        Index("ix_outbox_events_status_created", "status", "created_at"),
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
