import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from core.database import get_db
from core.redis import publish_event, set_with_ttl
from core.security import get_current_user
from jobs.celery_app import celery_app
from jobs.tasks import process_audio_ingestion, process_transcript_ingestion
from modules.identity.models import User
from modules.audit.service import record_audit_event
from modules.ingestion.models import IngestionJob
from modules.ingestion.service import IngestionService
from core.outbox.service import create_outbox_event
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Capture"])

AUDIO_UPLOAD_DIR = Path("/tmp/promisecheck_audio_uploads")
AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


@router.get("/jobs", response_model=list[IngestJobResponse])
async def list_ingest_jobs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List recent conversation ingestion tasks for the active workspace."""
    ws_id = await get_active_workspace_id(db, user)
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.workspace_id == ws_id)
        .order_by(desc(IngestionJob.created_at))
        .limit(20)
    )
    db_jobs = result.scalars().all()

    return [
        IngestJobResponse(
            job_id=j.job_id,
            source_type=j.source_type,
            status=j.status,
            candidates_extracted=j.candidates_extracted,
            candidates=j.candidates_json or [],
        )
        for j in db_jobs
    ]


@router.post("/upload", response_model=IngestJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_transcript(
    payload: UploadTranscriptRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload meeting transcript and dispatch to Celery for async AI extraction."""
    ws_id = await get_active_workspace_id(db, user)

    text_to_process = payload.transcript_text.strip()
    if not text_to_process:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="transcript_text must not be empty.",
        )

    res = await IngestionService.queue_transcript_ingestion(
        db=db,
        workspace_id=ws_id,
        user_id=user.id,
        customer=payload.customer,
        meeting_title=payload.meeting_title,
        transcript_text=text_to_process,
        source_type=payload.source_type,
    )
    return IngestJobResponse(**res)


@router.post("/upload-audio", response_model=IngestJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio_file(
    file: UploadFile = File(...),
    customer: str = Form("Acme"),
    meeting_title: str = Form("Recorded Customer Call"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Upload audio file (.mp3/.wav), stream to disk in chunks, and dispatch async Celery transcription."""
    MAX_AUDIO_SIZE = 200 * 1_000_000  # 200 MB
    job_id = f"job-aud-{uuid.uuid4().hex[:8]}"

    safe_suffix = Path(file.filename or "recording.mp3").suffix or ".mp3"
    dest_path = AUDIO_UPLOAD_DIR / f"{job_id}{safe_suffix}"
    total_bytes = 0

    try:
        with open(dest_path, "wb") as buffer:
            while True:
                read_res = file.read(64 * 1024)
                chunk = await read_res if hasattr(read_res, "__await__") else read_res
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_AUDIO_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Audio file exceeds 200 MB limit.",
                    )
                buffer.write(chunk if isinstance(chunk, (bytes, bytearray)) else b"")
                # If chunk returned more than requested or mock object, break
                if not isinstance(chunk, (bytes, bytearray)) or len(chunk) < 64 * 1024:
                    break
    except HTTPException:
        if dest_path.exists():
            dest_path.unlink()
        raise
    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save audio file: {exc}",
        )

    ws_id = await get_active_workspace_id(db, user)


    res = await IngestionService.queue_audio_ingestion(
        db=db,
        workspace_id=ws_id,
        user_id=user.id,
        file_path=dest_path,
        filename=file.filename,
        file_size_bytes=total_bytes,
        customer=customer,
        meeting_title=meeting_title,
    )
    return IngestJobResponse(**res)

