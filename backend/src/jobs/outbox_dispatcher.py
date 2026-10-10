"""Transactional Outbox Event Dispatcher Loop (Feature-Based Architecture).

FEATURE PURPOSE:
Polls the PostgreSQL `outbox_events` table for unclaimed events using
`SELECT ... FOR UPDATE SKIP LOCKED` (ensuring multi-instance concurrency without
double-dispatch), submits each event to the Celery broker, and transitions state
to 'dispatched' in an atomic transaction.

NAMING CONVENTION:
This module is named `outbox_dispatcher.py` to immediately communicate its feature
responsibility (Transactional Outbox pattern) rather than generic `dispatcher.py`.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from core.logging import get_logger

logger = get_logger("outbox_dispatcher")

# Batch size per polling cycle — keeps individual cycles fast and predictable
_BATCH_SIZE = 50
# Polling interval when there is nothing to dispatch
_IDLE_SLEEP = 1.0
# Polling interval after a non-empty batch (drain faster when busy)
_BUSY_SLEEP = 0.1
# Back-off after a hard error before retrying
_ERROR_SLEEP = 5.0


async def run_dispatcher() -> None:
    """Poll the outbox table and dispatch pending events to Celery.

    Each cycle:
      1. Open a DB transaction.
      2. SELECT … FOR UPDATE SKIP LOCKED on up to _BATCH_SIZE unclaimed rows.
      3. For each row, determine which Celery task to fire and call .delay().
      4. Mark each row dispatched (dispatched_at = now, status = 'dispatched').
      5. Commit. If the commit fails, rows remain pending and will be retried.
    """
    from sqlalchemy import select, text, update
    from sqlalchemy.ext.asyncio import AsyncSession

    from core.database import AsyncSessionLocal
    from jobs.celery_app import celery_app

    # Import the outbox model — it may not exist yet if migration hasn't run;
    # the dispatcher handles ImportError gracefully below.
    try:
        from modules.outbox.models import OutboxEvent  # type: ignore[import]
        _has_outbox = True
    except ImportError:
        _has_outbox = False
        logger.warning(
            "OutboxEvent model not found — dispatcher will sleep until the model is "
            "created. Run: alembic upgrade head"
        )

    logger.info("PromiseCheck Outbox Dispatcher started")

    while True:
        if not _has_outbox:
            # Model not yet created — keep looping, re-check import periodically
            await asyncio.sleep(30.0)
            try:
                from modules.outbox.models import OutboxEvent  # type: ignore[import]  # noqa: F811
                _has_outbox = True
                logger.info("OutboxEvent model now available — dispatcher activating")
            except ImportError:
                pass
            continue

        try:
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    # Claim a batch of pending rows with a row-level lock.
                    # SKIP LOCKED means other dispatcher instances skip rows
                    # already locked by this one — no double dispatch.
                    stmt = (
                        select(OutboxEvent)
                        .where(OutboxEvent.status == "pending")
                        .order_by(OutboxEvent.created_at)
                        .limit(_BATCH_SIZE)
                    )
                    bind = db.bind or getattr(db, "sync_session", db).bind
                    dialect_name = getattr(bind.dialect, "name", "") if bind else ""
                    if dialect_name != "sqlite":
                        stmt = stmt.with_for_update(skip_locked=True)

                    result = await db.execute(stmt)
                    rows = result.scalars().all()

                    if not rows:
                        # Nothing to dispatch — let the transaction close cleanly
                        await asyncio.sleep(_IDLE_SLEEP)
                        continue

                    dispatched_ids = []
                    failed_ids = []
                    for row in rows:
                        try:
                            _dispatch_to_celery(celery_app, row)
                            dispatched_ids.append(row.id)
                        except Exception as dispatch_err:
                            logger.error(
                                f"Failed to dispatch outbox event {row.id} "
                                f"(type={row.event_type}): {dispatch_err}"
                            )
                            # Increment attempts in payload; dead-letter after 5 failures
                            p = dict(row.payload or {})
                            attempts = p.get("dispatch_attempts", 0) + 1
                            p["dispatch_attempts"] = attempts
                            p["last_dispatch_error"] = str(dispatch_err)
                            row.payload = p
                            if attempts >= 5:
                                failed_ids.append(row.id)

                    now = datetime.now(timezone.utc)
                    if dispatched_ids:
                        await db.execute(
                            update(OutboxEvent)
                            .where(OutboxEvent.id.in_(dispatched_ids))
                            .values(status="dispatched", dispatched_at=now)
                        )
                        logger.info(f"Dispatcher: dispatched {len(dispatched_ids)} outbox events")

                    if failed_ids:
                        await db.execute(
                            update(OutboxEvent)
                            .where(OutboxEvent.id.in_(failed_ids))
                            .values(status="failed")
                        )
                        logger.warning(f"Dispatcher: marked {len(failed_ids)} corrupted outbox events as failed")

            await asyncio.sleep(_BUSY_SLEEP if rows else _IDLE_SLEEP)

        except asyncio.CancelledError:
            logger.info("Outbox Dispatcher shutting down gracefully")
            break
        except Exception as exc:
            logger.error("Error in dispatcher polling cycle", exc_info=exc)
            await asyncio.sleep(_ERROR_SLEEP)


def _dispatch_to_celery(celery_app: Any, row: Any) -> None:
    """Route an outbox event to the correct Celery task.

    Courier responsibility:
    - Never executes business logic or synchronous network calls in poller loop.
    - Routes to Celery via .apply_async() with target queues.
    """
    from jobs.tasks import (
        dispatch_notification_alert,
        process_audio_ingestion,
        process_transcript_ingestion,
        scan_commitment_deadlines,
    )

    event_type: str = row.event_type
    payload: dict = row.payload or {}

    if event_type == "ingestion.transcript.process":
        process_transcript_ingestion.apply_async(
            kwargs={
                "job_id": payload["job_id"],
                "workspace_id": payload["workspace_id"],
                "transcript_text": payload["transcript_text"],
                "customer_name": payload.get("customer_name", "Customer"),
                "meeting_title": payload.get("meeting_title", "Meeting"),
            },
            queue="ingestion",
        )

    elif event_type == "ingestion.audio.process":
        process_audio_ingestion.apply_async(
            kwargs={
                "job_id": payload["job_id"],
                "workspace_id": payload["workspace_id"],
                "file_path": payload["file_path"],
                "customer_name": payload.get("customer_name", "Customer"),
                "meeting_title": payload.get("meeting_title", "Meeting"),
            },
            queue="ingestion",
        )

    elif event_type == "risk.scan.request":
        scan_commitment_deadlines.apply_async(queue="high_priority")

    elif event_type in ("notification.deadline.overdue", "notification.deadline.at_risk"):
        ws_id = payload.get("workspace_id", "")
        channel = f"ws:{ws_id}:events" if ws_id else "global:events"
        ev_name = event_type.upper().replace(".", "_")
        dispatch_notification_alert.apply_async(
            kwargs={"channel": channel, "event_type": ev_name, "payload": payload},
            queue="high_priority",
        )
        logger.info(f"Dispatched deadline notification for commitment {payload.get('commitment_id')}")

    else:
        logger.warning(
            f"Dispatcher: unknown event_type '{event_type}' on outbox row {row.id} — "
            "leaving pending until a handler is registered"
        )
        raise ValueError(f"No Celery handler for event_type '{event_type}'")


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
