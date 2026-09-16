"""Ingestion jobs database model."""

import uuid
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TenantMixin


class IngestionJob(Base, TenantMixin):
    """Meeting transcript, call upload, and AI extraction job."""

    __tablename__ = "ingestion_jobs"

    job_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), default="General Customer", nullable=False)
    meeting_title: Mapped[str] = mapped_column(String(255), default="Customer Review", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="upload", nullable=False)  # upload, audio_upload, meet, zoom
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)    # queued, processing, completed, failed
    candidates_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transcript_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    candidates_json: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
