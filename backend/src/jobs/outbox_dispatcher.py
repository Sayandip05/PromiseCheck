"""Transactional Outbox Event Dispatcher Loop (Feature-Based Architecture).

FEATURE PURPOSE:
Polls the PostgreSQL `outbox_events` table for unclaimed events using
`SELECT ... FOR UPDATE SKIP LOCKED` (ensuring multi-instance concurrency without
double-dispatch), submits each event to the Celery broker, and transitions state
to 'dispatched' in an atomic transaction.

POISON-EVENT HANDLING:
Rows that fail dispatch are rescheduled via `next_retry_at` using exponential
backoff (2s, 4s, 8s, …). This prevents a single failing event at the head of the
queue from being re-selected on every poll cycle (retry storm / head-of-line
blocking). After `_MAX_DISPATCH_ATTEMPTS` the row is dead-lettered to 'failed'.

NAMING CONVENTION:
This module is named `outbox_dispatcher.py` to immediately communicate its feature
responsibility (Transactional Outbox pattern) rather than generic `dispatcher.py`.
"""

import asyncio
from datetime import datetime, timedelta, timezone
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

# Failure handling: dead-letter after this many failed attempts
_MAX_DISPATCH_ATTEMPTS = 5
# Exponential backoff base/cap (seconds) for retrying poison events
_BASE_BACKOFF_SECONDS = 2.0
_MAX_BACKOFF_SECONDS = 300.0


def _compute_backoff_seconds(attempts: int) -> float:
    """Return the exponential backoff delay for a poison event.

    ``attempts`` is the 1-based failure count (1 -> base, 2 -> 2x base, …),
    capped at ``_MAX_BACKOFF_SECONDS``.
    """
    exponent = max(0, attempts - 1)
    return min(_BASE_BACKOFF_SECONDS * (2**exponent), _MAX_BACKOFF_SECONDS)


async def dispatch_once() -> int:
    """Run a single polling cycle.

    Claims up to ``_BATCH_SIZE`` pending rows whose backoff window
    (``next_retry_at``) has elapsed, dispatches each to Celery, and persists the
    resulting state atomically. Failed rows are rescheduled via ``next_retry_at``
    so a poison event cannot block healthy events behind it; after
    ``_MAX_DISPATCH_ATTEMPTS`` they are marked 'failed'.

    Returns the number of rows newly marked 'dispatched' in this cycle.
    """
    from sqlalchemy import or_, select, update

    from core.database import AsyncSessionLocal
    from core.outbox.models import OutboxEvent
    from jobs.celery_app import celery_app

    dispatched_count = 0

    async with AsyncSessionLocal() as db:
        async with db.begin():
            now = datetime.now(timezone.utc)
            # Claim a batch of pending rows whose backoff has elapsed.
            # SKIP LOCKED means other dispatcher instances skip rows already
            # locked by this one — no double dispatch.
            stmt = (
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == "pending",
                    or_(
                        OutboxEvent.next_retry_at.is_(None),
                        OutboxEvent.next_retry_at <= now,
                    ),
                )
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
                return 0

            dispatched_ids: list[Any] = []
            failed_ids: list[Any] = []
            for row in rows:
                try:
                    _dispatch_to_celery(celery_app, row)
                    dispatched_ids.append(row.id)
                except Exception as dispatch_err:
                    logger.error(
                        f"Failed to dispatch outbox event {row.id} "
                        f"(type={row.event_type}): {dispatch_err}"
                    )
                    # Increment attempts in payload; dead-letter after max attempts.
                    p = dict(row.payload or {})
                    attempts = p.get("dispatch_attempts", 0) + 1
                    p["dispatch_attempts"] = attempts
                    p["last_dispatch_error"] = str(dispatch_err)
                    row.payload = p
                    if attempts >= _MAX_DISPATCH_ATTEMPTS:
                        failed_ids.append(row.id)
                    else:
                        # Exponential backoff: yield the head of the queue so
                        # healthy events are not blocked by this poison row.
                        row.next_retry_at = now + timedelta(
                            seconds=_compute_backoff_seconds(attempts)
                        )

            if dispatched_ids:
                await db.execute(
                    update(OutboxEvent)
                    .where(OutboxEvent.id.in_(dispatched_ids))
                    .values(status="dispatched", dispatched_at=now)
                )
                dispatched_count = len(dispatched_ids)
                logger.info(f"Dispatcher: dispatched {dispatched_count} outbox events")

            if failed_ids:
                await db.execute(
                    update(OutboxEvent)
                    .where(OutboxEvent.id.in_(failed_ids))
                    .values(status="failed")
                )
                logger.warning(f"Dispatcher: marked {len(failed_ids)} corrupted outbox events as failed")

    return dispatched_count


async def run_dispatcher() -> None:
    """Continuously poll the outbox table and dispatch pending events to Celery.

    Each cycle delegates to :func:`dispatch_once` (a single atomic transaction
    using ``FOR UPDATE SKIP LOCKED``), then sleeps briefly.
    """
    # Import the outbox model — it may not exist yet if migration hasn't run;
    # the dispatcher handles ImportError gracefully below.
    try:
        from core.outbox.models import OutboxEvent  # type: ignore[import]  # noqa: F401
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
                from core.outbox.models import OutboxEvent  # type: ignore[import]  # noqa: F401,F811
                _has_outbox = True
                logger.info("OutboxEvent model now available — dispatcher activating")
            except ImportError:
                pass
            continue

        try:
            dispatched = await dispatch_once()
            await asyncio.sleep(_BUSY_SLEEP if dispatched else _IDLE_SLEEP)
        except asyncio.CancelledError:
            logger.info("Outbox Dispatcher shutting down gracefully")
            break
        except Exception as exc:
            logger.error("Error in dispatcher polling cycle", exc_info=exc)
            await asyncio.sleep(_ERROR_SLEEP)


from core.outbox.registry import dispatch_event


def _dispatch_to_celery(celery_app: Any, row: Any) -> None:
    """Route an outbox event to the correct Celery task via core.outbox.registry.

    Courier responsibility:
    - Never executes business logic or synchronous network calls in poller loop.
    - Routes to Celery via send_task() with target queues without importing task objects.
    - Acknowledges explicit no-op lifecycle events without error or retry storm.
    """
    dispatch_event(celery_app, row)


if __name__ == "__main__":
    asyncio.run(run_dispatcher())
