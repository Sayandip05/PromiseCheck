"""Engineering ticket database models (FR-11 ticket sync).

Tickets are first-class rows keyed by workspace + provider + provider record ID
rather than being buried inside ``engineering_evidence_json``.  Commitment links
are many-to-many with reviewed confidence and required-delivery semantics.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class Ticket(Base, TenantMixin):
    """Normalized external engineering tracker ticket (Jira, Linear, GitHub)."""

    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "provider_ticket_id",
            name="uq_tickets_ws_provider_ticket",
        ),
        Index("ix_tickets_ws_status", "workspace_id", "status"),
    )

    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_ticket_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False, index=True)
    status_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class CommitmentTicket(Base, TenantMixin):
    """Reviewed many-to-many mapping between a commitment and an engineering ticket."""

    __tablename__ = "commitment_tickets"
    __table_args__ = (
        UniqueConstraint("commitment_id", "ticket_id", name="uq_commitment_tickets_pair"),
        Index("ix_commitment_tickets_ws_ticket", "workspace_id", "ticket_id"),
    )

    commitment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commitments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_for_delivery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Dependency(Base, TenantMixin):
    """Directed dependency between two engineering tickets."""

    __tablename__ = "dependencies"
    __table_args__ = (
        UniqueConstraint("ticket_id", "depends_on_ticket_id", name="uq_dependencies_pair"),
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type: Mapped[str] = mapped_column(String(50), default="blocks", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
