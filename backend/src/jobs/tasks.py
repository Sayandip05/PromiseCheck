"""Shared background asynchronous tasks registered on the unified Celery app."""

import uuid
from datetime import date
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


@celery_app.task(bind=True, queue="ingestion", max_retries=3, default_retry_delay=30)
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

    # 1. Update job status with 24-hour TTL in Redis
    set_with_ttl_sync(f"job:{job_id}", {"status": "processing", "progress": 10}, ttl_seconds=86400)

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
        set_with_ttl_sync(f"job:{job_id}", {"status": "failed", "error": str(exc)}, ttl_seconds=86400)
        try:
            with Session(_sync_engine) as session:
                from modules.ingestion.models import IngestionJob
                db_job = session.execute(
                    sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
                ).scalar_one_or_none()
                if db_job:
                    db_job.status = "failed"
                    # Preserve error details in DB so failed ingestion work is never lost silently
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

    # 3. Persist candidate commitments using the singleton engine (Fix #1)
    from sqlalchemy import select as sa_select
    from modules.ingestion.models import IngestionJob

    created_count = 0
    with Session(_sync_engine) as session:
        for item in candidates:
            # Parse the ISO date string from the extractor into a proper date object.
            _raw_date = item.get("promised_date_iso", "")
            _promised_date: date | None = None
            if _raw_date:
                try:
                    _promised_date = date.fromisoformat(_raw_date[:10])
                except ValueError:
                    _promised_date = None

            c = Commitment(
                workspace_id=uuid.UUID(workspace_id),
                title=item.get("title", "New commitment candidate"),
                customer_name=item.get("customer", customer_name),
                quote=item.get("quote", ""),
                promised_by=item.get("promised_by", "Upcoming"),
                promised_date=_promised_date,
                status="awaiting-review",
                status_label="Awaiting review",
                category="awaiting-review",
                is_confirmed=False,
                has_conflict=False,
                conflict_days=0,
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

        # Update the IngestionJob row with real status, candidates count, and json
        db_job = session.execute(
            sa_select(IngestionJob).where(IngestionJob.job_id == job_id)
        ).scalar_one_or_none()
        if db_job:
            db_job.status = "completed"
            db_job.candidates_extracted = created_count
            db_job.candidates_json = candidates

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


@celery_app.task(bind=True, queue="high_priority", max_retries=2)
def scan_commitment_deadlines(self) -> dict[str, Any]:
    """Periodic job: scan active commitments for overdue and at-risk status.

    Queries all active commitments whose due_date or promised_date has passed
    and updates their status to 'overdue'.  Commitments within 7 days of
    deadline are flagged 'at-risk'.  Only terminal statuses (delivered,
    canceled, superseded) are skipped.

    Atomically writes notification intent events into the transactional outbox.
    Uses a Redis distributed lock to prevent duplicate runs in multi-instance deployments.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select, update
    from sqlalchemy.orm import Session as SyncSession

    from modules.outbox.models import OutboxEvent

    # Distributed scheduler lock: prevent duplicate execution when multiple worker containers run Celery Beat
    try:
        if not celery_app.conf.task_always_eager:
            from core.redis import get_sync_redis
            r_client = get_sync_redis()
            acquired = r_client.set("lock:celery_beat:scan_deadlines", "active", nx=True, ex=300)
            if not acquired:
                logger.info("[Celery Worker] Risk scan already running on another instance (distributed lock held) — skipping duplicate")
                return {"status": "skipped", "reason": "distributed_lock_held", "updated_overdue": 0, "updated_at_risk": 0}
    except Exception as lock_err:
        logger.warning(f"[Celery Worker] Distributed lock check skipped: {lock_err}")

    logger.info("[Celery Worker] Running periodic commitment deadline risk evaluation")

    now = datetime.now(timezone.utc)
    at_risk_cutoff = now + timedelta(days=7)   # within 7 days → at-risk
    TERMINAL = {"delivered", "canceled", "superseded"}

    updated_overdue = 0
    updated_at_risk = 0

    with SyncSession(_sync_engine) as session:
        # Fetch all non-terminal commitments that have a date set
        stmt = select(Commitment).where(
            Commitment.status.not_in(TERMINAL),
            # at least one date column is populated
            (Commitment.due_date.isnot(None)) | (Commitment.promised_date.isnot(None)),
        )
        rows = session.execute(stmt).scalars().all()

        for c in rows:
            # Resolve the deadline: due_date (DateTime) wins over promised_date (Date)
            if c.due_date:
                deadline = (
                    c.due_date if c.due_date.tzinfo
                    else c.due_date.replace(tzinfo=timezone.utc)
                )
            elif c.promised_date:
                deadline = datetime(
                    c.promised_date.year,
                    c.promised_date.month,
                    c.promised_date.day,
                    tzinfo=timezone.utc,
                )
            else:
                continue

            if deadline < now:
                if c.status != "overdue":
                    c.status = "overdue"
                    c.status_label = "Overdue"
                    c.category = "needs-attention"
                    updated_overdue += 1

                    # Atomically trigger notification intent in transactional outbox
                    outbox_ev = OutboxEvent(
                        workspace_id=c.workspace_id,
                        event_type="notification.deadline.overdue",
                        payload={
                            "commitment_id": str(c.id),
                            "title": c.title,
                            "customer": c.customer_name,
                            "due_date": deadline.isoformat(),
                            "owner_email": c.owner_email,
                            "workspace_id": str(c.workspace_id),
                        },
                        status="pending",
                    )
                    session.add(outbox_ev)

            elif deadline < at_risk_cutoff:
                if c.status not in ("overdue", "at-risk"):
                    c.status = "at-risk"
                    c.status_label = "At risk"
                    c.category = "needs-attention"
                    updated_at_risk += 1

                    outbox_ev = OutboxEvent(
                        workspace_id=c.workspace_id,
                        event_type="notification.deadline.at_risk",
                        payload={
                            "commitment_id": str(c.id),
                            "title": c.title,
                            "customer": c.customer_name,
                            "due_date": deadline.isoformat(),
                            "owner_email": c.owner_email,
                            "workspace_id": str(c.workspace_id),
                        },
                        status="pending",
                    )
                    session.add(outbox_ev)

        if updated_overdue + updated_at_risk > 0:
            session.commit()

    result = {
        "status": "completed",
        "updated_overdue": updated_overdue,
        "updated_at_risk": updated_at_risk,
        "scanned_at": now.isoformat(),
    }

    publish_event_sync(
        "global:events",
        "RISK_EVALUATION_COMPLETED",
        result,
    )

    logger.info(
        f"[Celery Worker] Risk scan done: {updated_overdue} overdue, "
        f"{updated_at_risk} at-risk updated"
    )
    return result


@celery_app.task(bind=True, queue="default", max_retries=1)
def cleanup_expired_tokens(self) -> dict[str, int]:
    """Nightly batched deletion of expired refresh tokens and sessions.

    Deletes in LIMIT=1000 batches with a 50 ms sleep between each batch to
    avoid a single large DELETE holding a row-level lock and triggering an
    autovacuum storm on high-volume tables.

    Rows are only removed after they have been expired for at least 24 hours
    (expires_at < NOW() - 1 day) so in-flight token verifications that may
    still be reading the row are never raced.
    """
    import time
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import delete, select as sa_select
    from sqlalchemy.orm import Session as SyncSession

    from modules.identity.models import RefreshToken
    from modules.identity.models import Session as UserSession

    logger.info("[Celery Worker] Starting nightly expired token cleanup")
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    batch_size = 1000
    total_tokens = 0
    total_sessions = 0

    with SyncSession(_sync_engine) as session:
        # ── Refresh tokens ───────────────────────────────────────────────────
        while True:
            # Fetch a batch of IDs to delete (avoids large lock escalation)
            ids = session.execute(
                sa_select(RefreshToken.id)
                .where(RefreshToken.expires_at < cutoff)
                .limit(batch_size)
            ).scalars().all()
            if not ids:
                break
            result = session.execute(
                delete(RefreshToken).where(RefreshToken.id.in_(ids))
            )
            session.commit()
            total_tokens += result.rowcount
            if result.rowcount < batch_size:
                break
            time.sleep(0.05)  # 50 ms breathing room between batches

        # ── Sessions ─────────────────────────────────────────────────────────
        while True:
            ids = session.execute(
                sa_select(UserSession.id)
                .where(UserSession.expires_at < cutoff)
                .limit(batch_size)
            ).scalars().all()
            if not ids:
                break
            result = session.execute(
                delete(UserSession).where(UserSession.id.in_(ids))
            )
            session.commit()
            total_sessions += result.rowcount
            if result.rowcount < batch_size:
                break
            time.sleep(0.05)

    logger.info(
        f"[Celery Worker] Token cleanup complete: "
        f"{total_tokens} refresh tokens, {total_sessions} sessions deleted"
    )
    return {"refresh_tokens_deleted": total_tokens, "sessions_deleted": total_sessions}
