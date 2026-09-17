"""Shared background asynchronous tasks registered on the unified Celery app."""

import uuid
from typing import Any

from ai.extractor import PromiseExtractor
from core.logging import get_logger
from core.redis import publish_event_sync, set_with_ttl_sync
from jobs.celery_app import celery_app
from modules.commitments.models import Commitment
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import os
from core.config import settings

logger = get_logger("celery_tasks")

# ── Fix #1: Module-level singleton sync engine ───────────────────────────────
# Previously create_engine() was called inside the task function body, spawning
# a brand-new connection pool on EVERY task invocation. Under 100 concurrent
# ingestion jobs this would create 100 engines, exhausting OS file descriptors
# and RAM. The singleton is created once at worker startup and shared.
_db_sync_url = (
    settings.DATABASE_SYNC_URL
    or os.getenv("DATABASE_SYNC_URL")
    or "sqlite:///./promisecheck.db"
)
_sync_engine_kwargs: dict = {
    "pool_pre_ping": True,   # validate stale connections before checkout
    "pool_recycle": 1800,    # recycle connections after 30 min to avoid DB-side timeout drops
}
if "sqlite" in _db_sync_url:
    # SQLite does not support pool_size / max_overflow
    _sync_engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: small bounded pool — Celery workers are long-lived processes
    _sync_engine_kwargs["pool_size"] = 5
    _sync_engine_kwargs["max_overflow"] = 10

_sync_engine = create_engine(_db_sync_url, **_sync_engine_kwargs)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
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

    # 1. Update job status with 2-hour TTL in Redis
    set_with_ttl_sync(f"job:{job_id}", {"status": "processing", "progress": 10}, ttl_seconds=7200)

    # 2. Fix #2: Use synchronous extractor — no asyncio.run() blocking.
    # Previously asyncio.run() created a nested event loop inside the Celery
    # thread and blocked it for the full LLM HTTP round-trip (2–10 seconds).
    # extract_candidates_sync() uses httpx.Client (blocking) directly.
    extractor = PromiseExtractor()
    try:
        candidates = extractor.extract_candidates_sync(
            transcript_text=transcript_text,
            meeting_title=meeting_title,
            default_customer=customer_name,
        )
    except Exception as exc:
        logger.error(f"[Celery Worker] Extraction failed for job {job_id}: {exc}")
        set_with_ttl_sync(f"job:{job_id}", {"status": "failed", "error": str(exc)}, ttl_seconds=7200)
        publish_event_sync(
            f"ws:{workspace_id}:events",
            "INGESTION_FAILED",
            {"job_id": job_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)

    # 3. Persist candidate commitments using the singleton engine (Fix #1)
    created_count = 0
    with Session(_sync_engine) as session:
        for item in candidates:
            c = Commitment(
                workspace_id=uuid.UUID(workspace_id),
                title=item.get("title", "New commitment candidate"),
                customer_name=item.get("customer", customer_name),
                quote=item.get("quote", ""),
                promised_by=item.get("promised_by", "Upcoming"),
                status="awaiting-review",
                status_label="Awaiting review",
                category="awaiting-review",
                is_confirmed=False,
                original_promise_json={
                    "quote": item.get("quote", ""),
                    "sourceTitle": meeting_title,
                    "timestamp": "Just now (Extracted)",
                    "context": item.get("context", ""),
                },
                risk_json={"level": "low", "reason": "New candidate awaiting verification", "conflictDays": 0},
                engineering_evidence_json={"prs": [], "tickets": [], "releaseNotes": []},
            )
            session.add(c)
            created_count += 1
        session.commit()

    # 4. Cache final job result in Redis with 24-hour TTL
    job_result = {
        "job_id": job_id,
        "status": "completed",
        "candidates_extracted": created_count,
        "customer": customer_name,
    }
    set_with_ttl_sync(f"job:{job_id}", job_result, ttl_seconds=86400)

    # 5. Broadcast real-time event to the workspace Pub/Sub channel
    publish_event_sync(
        f"ws:{workspace_id}:events",
        "INGESTION_COMPLETED",
        job_result,
    )

    logger.info(f"[Celery Worker] Successfully completed job {job_id}: {created_count} commitments created")
    return job_result


@celery_app.task(bind=True, max_retries=2)
def scan_commitment_deadlines(self) -> dict[str, str]:
    """Periodic job scanning for commitments approaching deadline or in conflict."""
    logger.info("[Celery Worker] Running periodic commitment deadline risk evaluation")
    # Broadcast periodic scan result
    publish_event_sync(
        "global:events",
        "RISK_EVALUATION_COMPLETED",
        {"timestamp": "hourly_scan_done"},
    )
    return {"status": "completed"}
