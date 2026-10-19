"""Notification approval and delivery database models (FR-13 / FR-14).

Sending a customer-facing update is a two-step, approval-gated, idempotent
operation: a draft is created and hashed, an approval authorises the exact
content hash, and each provider attempt is recorded so ambiguous sends can be
recovered rather than blindly retried.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class NotificationDraft(Base, TenantMixin):
    """Human-reviewable customer notification draft with a content hash for dedup."""

    __tablename__ = "notification_drafts"
    __table_args__ = (
        Index("ix_notification_drafts_ws_hash", "workspace_id", "content_hash"),
        Index("ix_notification_drafts_ws_status", "workspace_id", "status"),
    )

    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commitments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subject: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False, index=True
    )  # draft, approved, sending, sent, failed, cancelled
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Approval(Base, TenantMixin):
    """Explicit approval authorising one exact draft content hash to be sent."""

    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approvals_ws_draft", "workspace_id", "draft_id"),)

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    decision: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, approved, rejected
    # The content hash the approver reviewed.  A send only proceeds when the
    # current draft hash still matches this value (exact-approval sending).
    expected_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class NotificationAttempt(Base, TenantMixin):
    """One provider delivery attempt for a draft, used for idempotent recovery."""

    __tablename__ = "notification_attempts"
    __table_args__ = (
        Index("ix_notification_attempts_ws_draft", "workspace_id", "draft_id"),
        UniqueConstraint(
            "workspace_id",
            "request_fingerprint",
            name="uq_notification_attempts_fingerprint",
        ),
    )

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approvals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, sent, failed, ambiguous
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
