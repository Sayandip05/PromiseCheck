"""Ingestion router for transcripts, meetings, and conversation uploads."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Capture"])


class IngestJobResponse(BaseModel):
    """Asynchronous ingestion job state."""

    job_id: str
    source_type: str  # meet, zoom, teams, email, upload
    status: str  # queued, processing, completed, failed


@router.get("/jobs", response_model=list[IngestJobResponse])
async def list_ingest_jobs():
    """List recent conversation ingestion tasks."""
    return []
