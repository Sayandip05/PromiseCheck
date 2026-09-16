"""Ingestion router for transcripts, meetings, and conversation uploads."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ai.extractor import PromiseExtractor
from connectors.speech_to_text import SpeechToTextConnector
from core.database import get_db
from core.redis import publish_event, set_with_ttl
from core.security import get_current_user, get_current_user_optional
from modules.commitments.models import Commitment
from modules.commitments.router import _to_dto
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id
from sqlalchemy import desc, select
from modules.audit.service import record_audit_event
from modules.ingestion.models import IngestionJob

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Capture"])


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
    user: Optional[User] = Depends(get_current_user_optional),
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

    if db_jobs:
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

    # Fallback seed jobs if none yet uploaded in this workspace
    return [
        IngestJobResponse(
            job_id="job-rec-8823",
            source_type="meet",
            status="completed",
            candidates_extracted=1,
            candidates=[{"title": "Enable SSO", "customer": "Acme"}],
        ),
        IngestJobResponse(
            job_id="job-rec-8741",
            source_type="zoom",
            status="completed",
            candidates_extracted=1,
            candidates=[{"title": "Export audit logs", "customer": "Northstar"}],
        ),
    ]


@router.post("/upload", response_model=IngestJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_transcript(
    payload: UploadTranscriptRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Upload meeting transcript, extract commitments using Groq LLM, and queue for human review."""
    ws_id = await get_active_workspace_id(db, user)

    text_to_process = payload.transcript_text.strip()
    if not text_to_process:
        # Default sample transcript if none provided
        text_to_process = (
            f"During the {payload.meeting_title} with {payload.customer}, Maya Chen confirmed: "
            f"'We will enable custom webhook integrations and deliver the sandbox testing environment by next Friday.' "
            f"The client agreed this was their primary blocker for production migration."
        )

    extractor = PromiseExtractor()
    extracted_candidates = await extractor.extract_candidates(text_to_process)

    created_commitments = []
    job_id = f"job-up-{uuid.uuid4().hex[:8]}"

    for cand in extracted_candidates:
        title = cand.get("title", "Review discussed deliverable")
        quote = cand.get("quote", text_to_process[:150])
        customer_name = cand.get("customer") or payload.customer
        promised_by = cand.get("promised_by", "Upcoming")
        promised_iso = cand.get("promised_date_iso", "")

        commitment = Commitment(
            workspace_id=ws_id,
            title=title,
            customer_name=customer_name,
            owner_name=user.full_name if user else "Lead Engineer",
            owner_email=user.email if user else "lead@acme.corp",
            promised_by=promised_by,
            promised_date_iso=promised_iso,
            status="awaiting-review",
            status_label="Awaiting review",
            is_confirmed=False,
            category="awaiting-review",
            quote=quote,
            original_promise_json={
                "quote": quote,
                "sourceTitle": payload.meeting_title,
                "timestamp": datetime.now(timezone.utc).strftime("%b %d · %H:%M"),
                "transcriptId": job_id,
            },
            engineering_evidence_json={},
            risk_json={"hasConflict": False},
            recommended_step_json={
                "text": "Review candidate promise extracted by AI.",
                "actionType": "review",
            },
        )
        db.add(commitment)
        created_commitments.append(cand)

    # Persist IngestionJob entity in database
    db_job = IngestionJob(
        workspace_id=ws_id,
        job_id=job_id,
        customer_name=payload.customer,
        meeting_title=payload.meeting_title,
        source_type=payload.source_type,
        status="completed",
        candidates_extracted=len(created_commitments),
        transcript_preview=text_to_process[:300],
        candidates_json=created_commitments,
    )
    db.add(db_job)

    # Record immutable audit event
    await record_audit_event(
        db=db,
        workspace_id=ws_id,
        actor_id=user.id if user else ws_id,
        action="TRANSCRIPT_INGESTED",
        target_type="ingestion_job",
        target_id=job_id,
        description=f"Extracted {len(created_commitments)} candidates from {payload.meeting_title} ({payload.customer}).",
        payload={"source_type": payload.source_type, "candidates_count": len(created_commitments)},
    )

    await db.commit()

    job_result = IngestJobResponse(
        job_id=job_id,
        source_type=payload.source_type,
        status="completed",
        candidates_extracted=len(created_commitments),
        candidates=created_commitments,
    )

    # 1. Cache job state in Redis with 24-hour TTL (auto-expires)
    await set_with_ttl(f"job:{job_id}", job_result.model_dump(), ttl_seconds=86400)

    # 2. Publish real-time event to workspace Pub/Sub channel
    await publish_event(
        f"ws:{ws_id}:events",
        "INGESTION_COMPLETED",
        {
            "job_id": job_id,
            "candidates_count": len(created_commitments),
            "customer": payload.customer,
            "meeting_title": payload.meeting_title,
        },
    )

    return job_result


@router.post("/upload-audio", response_model=IngestJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    file: UploadFile = File(...),
    customer: str = Form("Acme"),
    meeting_title: str = Form("Recorded Customer Call"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Upload audio file (.mp3/.wav), transcribe via SpeechToTextConnector, and extract promises."""
    content = await file.read()
    stt = SpeechToTextConnector()
    transcript_text = await stt.transcribe_audio(content, filename=file.filename or "recording.mp3")

    req = UploadTranscriptRequest(
        customer=customer,
        meeting_title=meeting_title,
        transcript_text=transcript_text,
        source_type="audio_upload",
    )
    return await upload_transcript(req, db, user)
