"""Ingestion domain Pydantic schemas."""

from typing import Any

from pydantic import BaseModel


class UploadTranscriptRequest(BaseModel):
    """Payload to upload and parse a meeting transcript."""

    customer: str = "Acme"
    meeting_title: str = "Customer Sync & Feature Review"
    transcript_text: str = ""
    source_type: str = "upload"  # meet, zoom, upload, slack


class IngestJobResponse(BaseModel):
    """Ingestion job execution result."""

    job_id: str
    source_type: str
    status: str
    candidates_extracted: int
    candidates: list[dict[str, Any]] = []
