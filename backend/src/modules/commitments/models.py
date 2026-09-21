"""Commitments database model."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class Commitment(Base, TenantMixin):
    """Captured customer commitment entity with evidence and risk tracking."""

    __tablename__ = "commitments"

    # ── Composite indexes on the hottest query paths ──────────────────────────
    # Added as __table_args__ so SQLAlchemy/Alembic can track and migrate them.
    # Use CREATE INDEX CONCURRENTLY in production to avoid table locks.
    __table_args__ = (
        # list_commitments: workspace_id + status filter (most common dashboard query)
        Index("ix_commitments_ws_status", "workspace_id", "status"),
        # list_commitments: workspace_id + category filter (dashboard tab counts)
        Index("ix_commitments_ws_category", "workspace_id", "category"),
        # scan_commitment_deadlines: overdue detection without full table scan
        Index("ix_commitments_ws_due_date", "workspace_id", "due_date"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), default="General Customer", nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Owner info
    owner_name: Mapped[str] = mapped_column(String(255), default="Team Lead", nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), default="lead@acme.corp", nullable=False)

    # Dates
    # promised_by: human-readable display string (e.g. "Sep 30, 2026")
    promised_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    # promised_date: authoritative Date column — replaces the old String promised_date_iso.
    # Use due_date (DateTime) for deadline enforcement; promised_date for display precision.
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status & Workflow
    # Single-column indexes kept for ORDER BY and individual lookups.
    # Composite indexes above cover the AND-filter hot paths.
    status: Mapped[str] = mapped_column(
        String(50), default="awaiting-review", nullable=False, index=True
    )  # at-risk, overdue, blocked, confirmed, delivered, awaiting-review
    status_label: Mapped[str] = mapped_column(String(50), default="Awaiting review", nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="awaiting-review", nullable=False, index=True
    )  # needs-attention, awaiting-review, on-track, delivered
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── First-class risk & ticket columns (Fix 4) ─────────────────────────────
    # Previously buried in opaque JSONB blobs, these fields are needed for DB-level
    # queries: "all blocked commitments", "conflict day count > 5", risk scans.
    # The full provider-specific metadata stays in engineering_evidence_json / risk_json.
    ticket_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    ticket_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conflict_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Evidence, Analysis & Steps JSON payloads (provider metadata, full detail)
    quote: Mapped[str] = mapped_column(Text, default="", nullable=False)
    original_promise_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    engineering_evidence_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    risk_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recommended_step_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
