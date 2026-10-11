"""Ingestion Celery background tasks."""

import os
from typing import Any

from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from ai.promise_extractor import PromiseExtractor
from core.database import sync_engine
from core.logging import get_logger
from core.redis import publish_event_sync, set_with_ttl_sync
from jobs.celery_app import celery_app
from modules.commitments import CommitmentService
from modules.ingestion.models import IngestionJob

logger = get_logger("modules.ingestion.tasks")


def _extract_and_persist_commitments(
    job_id: str,
    workspace_id: str,
    transcript_text: str,
    customer_name: str,
    meeting_title: str,
) -> dict[str, Any]:
    """Helper: Run sync LLM promise extraction and persist candidates to DB."""
    extractor = PromiseExtractor()
    candidates = extractor.extract_candidates_sync(
        transcript_text=transcript_text,
        meeting_title=meeting_title,
        default_customer=customer_name,
    )

    with Session(sync_engine) as session:
        created_count = CommitmentService.create_candidate_commitments_batch_sync(
            session=session,
            workspace_id=workspace_id,
            candidates=candidates,
            meeting_title=meeting_title,
            customer_name=customer_name,
        )

        db_job = session.execute(
            sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one_or_none()
        if db_job:
            db_job.status = "completed"
            db_job.candidates_extracted = created_count
            db_job.candidates_json = candidates

        session.commit()

    job_result = {
        "job_id": job_id,
        "status": "completed",
        "candidates_extracted": created_count,
        "customer": customer_name,
    }
    set_with_ttl_sync(f"job:{job_id}", job_result, ttl_seconds=86400)

    publish_event_sync(
        f"ws:{workspace_id}:events",
        "INGESTION_COMPLETED",
        job_result,
    )

    logger.info(f"[Celery Worker] Successfully completed job {job_id}: {created_count} commitments created")
    return job_result


@celery_app.task(
    name="jobs.tasks.process_transcript_ingestion",
    bind=True,
    queue="ingestion",
    max_retries=3,
    default_retry_delay=30,
)
def process_transcript_ingestion(
    self,
    job_id: str,
    workspace_id: str,
    transcript_text: str,
    customer_name: str = "Acme",
    meeting_title: str = "Meeting Sync",
) -> dict[str, Any]:
    """Background task: Parse transcript via Groq LLM, persist candidate commitments, and publish event."""
    logger.info(f"[Celery Worker] Starting transcript ingestion job: {job_id} for workspace {workspace_id}")
    set_with_ttl_sync(f"job:{job_id}", {"status": "processing", "progress": 10}, ttl_seconds=86400)

    try:
        return _extract_and_persist_commitments(
            job_id=job_id,
            workspace_id=workspace_id,
            transcript_text=transcript_text,
            customer_name=customer_name,
            meeting_title=meeting_title,
        )
    except Exception as exc:
        logger.error(f"[Celery Worker] Extraction failed for job {job_id}: {exc}")
        set_with_ttl_sync(f"job:{job_id}", {"status": "failed", "error": str(exc)}, ttl_seconds=86400)
        try:
            with Session(sync_engine) as session:
                db_job = session.execute(
                    sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
                ).scalar_one_or_none()
                if db_job:
                    db_job.status = "failed"
                    db_job.candidates_json = {"error": str(exc), "status": "failed_dead_letter"}
                    session.commit()
        except Exception as db_err:
            logger.warning(f"Failed to update IngestionJob status on failure: {db_err}")

        publish_event_sync(
            f"ws:{workspace_id}:events",
            "INGESTION_FAILED",
            {"job_id": job_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="jobs.tasks.process_audio_ingestion",
    bind=True,
    queue="ingestion",
    max_retries=3,
    default_retry_delay=30,
)
def process_audio_ingestion(
    self,
    job_id: str,
    workspace_id: str,
    file_path: str,
    customer_name: str = "Acme",
    meeting_title: str = "Recorded Call",
) -> dict[str, Any]:
    """Background task: Transcribe audio file via STT connector, extract promises, and persist."""
    logger.info(f"[Celery Worker] Starting audio ingestion job: {job_id} for workspace {workspace_id}")
    from connectors.speech_to_text import SpeechToTextConnector

    set_with_ttl_sync(f"job:{job_id}", {"status": "transcribing", "progress": 15}, ttl_seconds=86400)

    try:
        stt = SpeechToTextConnector()
        transcript_text = stt.transcribe_file_sync(file_path)
    except Exception as exc:
        logger.error(f"[Celery Worker] Speech-to-text failed for job {job_id}: {exc}")
        set_with_ttl_sync(f"job:{job_id}", {"status": "failed", "error": str(exc)}, ttl_seconds=86400)
        try:
            with Session(sync_engine) as session:
                db_job = session.execute(
                    sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
                ).scalar_one_or_none()
                if db_job:
                    db_job.status = "failed"
                    db_job.candidates_json = {"error": str(exc), "status": "failed_dead_letter"}
                    session.commit()
        except Exception as db_err:
            logger.warning(f"Failed to update IngestionJob status on failure: {db_err}")

        publish_event_sync(
            f"ws:{workspace_id}:events",
            "INGESTION_FAILED",
            {"job_id": job_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)
    finally:
        # Guarantee audio file is removed from disk so storage is never leaked
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    # Update preview in IngestionJob
    try:
        with Session(sync_engine) as session:
            db_job = session.execute(
                sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
            ).scalar_one_or_none()
            if db_job:
                db_job.transcript_preview = transcript_text[:300]
                session.commit()
    except Exception as preview_err:
        logger.warning(f"Failed to update transcript preview: {preview_err}")

    # Run promise extraction and persistence
    try:
        return _extract_and_persist_commitments(
            job_id=job_id,
            workspace_id=workspace_id,
            transcript_text=transcript_text,
            customer_name=customer_name,
            meeting_title=meeting_title,
        )
    except Exception as exc:
        logger.error(f"[Celery Worker] Extraction failed for audio job {job_id}: {exc}")
        set_with_ttl_sync(f"job:{job_id}", {"status": "failed", "error": str(exc)}, ttl_seconds=86400)
        try:
            with Session(sync_engine) as session:
                db_job = session.execute(
                    sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
                ).scalar_one_or_none()
                if db_job:
                    db_job.status = "failed"
                    db_job.candidates_json = {"error": str(exc), "status": "failed_dead_letter"}
                    session.commit()
        except Exception as db_err:
            logger.warning(f"Failed to update IngestionJob status on failure: {db_err}")

        publish_event_sync(
            f"ws:{workspace_id}:events",
            "INGESTION_FAILED",
            {"job_id": job_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)
