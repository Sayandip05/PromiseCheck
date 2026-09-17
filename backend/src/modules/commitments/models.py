"""Commitments database model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class Commitment(Base, TenantMixin):
    """Captured customer commitment entity with evidence and risk tracking."""

    __tablename__ = "commitments"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), default="General Customer", nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Owner info
    owner_name: Mapped[str] = mapped_column(String(255), default="Team Lead", nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), default="lead@acme.corp", nullable=False)

    # Dates
    promised_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    promised_date_iso: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status & Workflow
    status: Mapped[str] = mapped_column(
        String(50), default="awaiting-review", nullable=False, index=True
    )  # at-risk, overdue, blocked, confirmed, delivered, awaiting-review
    status_label: Mapped[str] = mapped_column(String(50), default="Awaiting review", nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="awaiting-review", nullable=False, index=True
    )  # needs-attention, awaiting-review, on-track, delivered
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Evidence, Analysis & Steps JSON payloads
    quote: Mapped[str] = mapped_column(Text, default="", nullable=False)
    original_promise_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    engineering_evidence_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    risk_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recommended_step_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
