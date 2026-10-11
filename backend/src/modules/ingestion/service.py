"""Ingestion domain service for meeting transcripts, audio files, and background job coordination."""

import os
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.redis import publish_event, set_with_ttl
from jobs.celery_app import celery_app
from modules.ingestion.tasks import process_audio_ingestion, process_transcript_ingestion
from modules.audit.service import record_audit_event
from modules.ingestion.models import IngestionJob
from core.outbox.service import create_outbox_event

logger = get_logger("ingestion_service")


class IngestionService:
    """Encapsulates transcript and audio ingestion job lifecycle."""

    @staticmethod
    async def queue_transcript_ingestion(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: str,
        meeting_title: str,
        transcript_text: str,
        source_type: str = "upload",
    ) -> dict[str, Any]:
        """Create ingestion job record, audit log, and outbox intent for transcript processing."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"

        db_job = IngestionJob(
            workspace_id=workspace_id,
            job_id=job_id,
            source_type=source_type,
            status="queued",
            candidates_extracted=0,
            transcript_preview=transcript_text[:300],
            candidates_json=[],
        )
        db.add(db_job)

        await record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor_id=user_id,
            action="TRANSCRIPT_QUEUED",
            target_type="ingestion_job",
            target_id=job_id,
            description=f"Queued transcript ingestion for {meeting_title} ({customer}).",
            payload={"source_type": source_type},
        )

        # Durable intent written in PostgreSQL outbox
        await create_outbox_event(
            db=db,
            workspace_id=workspace_id,
            event_type="ingestion.transcript.process",
            payload={
                "job_id": job_id,
                "workspace_id": str(workspace_id),
                "transcript_text": transcript_text,
                "customer_name": customer,
                "meeting_title": meeting_title,
            },
        )
        await db.commit()

        # Cache queued status in Redis with 24h TTL
        await set_with_ttl(f"job:{job_id}", {"status": "queued", "job_id": job_id}, ttl_seconds=86400)

        # Execute eagerly if test suite sets task_always_eager
        if getattr(celery_app.conf, "task_always_eager", False):
            process_transcript_ingestion.apply_async(
                kwargs={
                    "job_id": job_id,
                    "workspace_id": str(workspace_id),
                    "transcript_text": transcript_text,
                    "customer_name": customer,
                    "meeting_title": meeting_title,
                },
                queue="ingestion",
            )

        # Notify browser tabs
        await publish_event(
            f"ws:{workspace_id}:events",
            "INGESTION_QUEUED",
            {
                "job_id": job_id,
                "customer": customer,
                "meeting_title": meeting_title,
                "message": "Extraction in progress. You will be notified when complete.",
            },
        )

        return {
            "job_id": job_id,
            "source_type": source_type,
            "status": "queued",
            "candidates_extracted": 0,
            "candidates": [],
        }

    @staticmethod
    async def queue_audio_ingestion(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        file_path: Path,
        filename: str,
        file_size_bytes: int,
        customer: str,
        meeting_title: str,
    ) -> dict[str, Any]:
        """Create ingestion job record, audit log, and outbox intent for audio processing."""
        job_id = f"job-audio-{uuid.uuid4().hex[:8]}"

        db_job = IngestionJob(
            workspace_id=workspace_id,
            job_id=job_id,
            source_type="audio_upload",
            status="queued",
            candidates_extracted=0,
            transcript_preview=f"Audio recording: {filename} ({file_size_bytes // 1024} KB)",
            candidates_json=[],
        )
        db.add(db_job)

        await record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor_id=user_id,
            action="AUDIO_UPLOAD_QUEUED",
            target_type="ingestion_job",
            target_id=job_id,
            description=f"Queued audio upload for {meeting_title} ({customer}).",
            payload={"filename": filename, "file_size_bytes": file_size_bytes},
        )

        await create_outbox_event(
            db=db,
            workspace_id=workspace_id,
            event_type="ingestion.audio.process",
            payload={
                "job_id": job_id,
                "workspace_id": str(workspace_id),
                "file_path": str(file_path),
                "customer_name": customer,
                "meeting_title": meeting_title,
            },
        )
        await db.commit()

        await set_with_ttl(f"job:{job_id}", {"status": "queued", "job_id": job_id}, ttl_seconds=86400)

        if getattr(celery_app.conf, "task_always_eager", False):
            process_audio_ingestion.apply_async(
                kwargs={
                    "job_id": job_id,
                    "workspace_id": str(workspace_id),
                    "file_path": str(file_path),
                    "customer_name": customer,
                    "meeting_title": meeting_title,
                },
                queue="ingestion",
            )

        await publish_event(
            f"ws:{workspace_id}:events",
            "INGESTION_QUEUED",
            {
                "job_id": job_id,
                "customer": customer,
                "meeting_title": meeting_title,
                "message": "Audio transcription in progress. You will be notified when complete.",
            },
        )

        return {
            "job_id": job_id,
            "source_type": "audio_upload",
            "status": "queued",
            "candidates_extracted": 0,
            "candidates": [],
        }
