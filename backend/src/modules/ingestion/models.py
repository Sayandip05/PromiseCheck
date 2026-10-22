"""Ingestion jobs and evidence-lineage database models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class IngestionJob(Base, TenantMixin):
    """Meeting transcript, call upload, and AI extraction job."""

    __tablename__ = "ingestion_jobs"

    job_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(
        String(255), default="General Customer", nullable=False
    )
    meeting_title: Mapped[str] = mapped_column(
        String(255), default="Customer Review", nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(50), default="upload", nullable=False
    )  # upload, audio_upload, meet, zoom
    status: Mapped[str] = mapped_column(
        String(50), default="completed", nullable=False
    )  # queued, processing, completed, failed
    candidates_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transcript_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    candidates_json: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)


class SourceDocument(Base, TenantMixin):
    """An authoritative external source document (meeting, ticket, drive file, email).

    Evidence lineage (FR-07 / NFR-08) starts here: every commitment quote must be
    traceable to an immutable source version and segment offsets.
    """

    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "provider_document_id",
            name="uq_source_documents_ws_provider_doc",
        ),
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_document_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class SourceVersion(Base, TenantMixin):
    """Immutable revision of a source document.  Edits create a new version."""

    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_source_versions_doc_version"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class SourceSegment(Base, TenantMixin):
    """Addressable span of a source version, referenced by evidence links."""

    __tablename__ = "source_segments"
    __table_args__ = (
        UniqueConstraint("version_id", "segment_index", name="uq_source_segments_version_index"),
        Index("ix_source_segments_doc_index", "document_id", "segment_index"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
