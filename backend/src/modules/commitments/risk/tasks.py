"""Commitment risk scan Celery background tasks."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import sync_engine
from core.logging import get_logger
from core.outbox.models import OutboxEvent
from core.redis import publish_event_sync
from jobs.celery_app import celery_app
from modules.commitments.models import Commitment

logger = get_logger("modules.commitments.risk.tasks")


@celery_app.task(
    name="jobs.tasks.scan_commitment_deadlines",
    bind=True,
    queue="high_priority",
    max_retries=2,
)
def scan_commitment_deadlines(self) -> dict[str, Any]:
    """Periodic job: scan active commitments for overdue and at-risk status.

    Queries all active commitments whose due_date or promised_date has passed
    and updates their status to 'overdue'. Commitments within 7 days of
    deadline are flagged 'at-risk'. Only terminal statuses (delivered,
    canceled, superseded) are skipped.

    Atomically writes notification intent events into the transactional outbox.
    Uses a Redis distributed lock to prevent duplicate runs in multi-instance deployments.
    """
    # Distributed scheduler lock: prevent duplicate execution when multiple worker containers run Celery Beat
    try:
        if not celery_app.conf.task_always_eager:
            from core.redis import get_sync_redis

            r_client = get_sync_redis()
            acquired = r_client.set("lock:celery_beat:scan_deadlines", "active", nx=True, ex=300)
            if not acquired:
                logger.info(
                    "[Celery Worker] Risk scan already running on another instance (distributed lock held) — skipping duplicate"
                )
                return {
                    "status": "skipped",
                    "reason": "distributed_lock_held",
                    "updated_overdue": 0,
                    "updated_at_risk": 0,
                }
    except Exception as lock_err:
        logger.warning(f"[Celery Worker] Distributed lock check skipped: {lock_err}")

    logger.info("[Celery Worker] Running periodic commitment deadline risk evaluation")

    now = datetime.now(timezone.utc)
    at_risk_cutoff = now + timedelta(days=7)  # within 7 days -> at-risk
    TERMINAL = {"delivered", "canceled", "superseded"}

    updated_overdue = 0
    updated_at_risk = 0
    pending_alerts: list[tuple[str, str, dict[str, Any]]] = []

    with Session(sync_engine) as session:
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
                    c.due_date
                    if c.due_date.tzinfo
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

                    pending_alerts.append((
                        f"ws:{c.workspace_id}:events",
                        "NOTIFICATION_DEADLINE_OVERDUE",
                        {
                            "commitment_id": str(c.id),
                            "title": c.title,
                            "customer": c.customer_name,
                            "due_date": deadline.isoformat(),
                            "owner_email": c.owner_email,
                            "workspace_id": str(c.workspace_id),
                        },
                    ))

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

                    pending_alerts.append((
                        f"ws:{c.workspace_id}:events",
                        "NOTIFICATION_DEADLINE_AT_RISK",
                        {
                            "commitment_id": str(c.id),
                            "title": c.title,
                            "customer": c.customer_name,
                            "due_date": deadline.isoformat(),
                            "owner_email": c.owner_email,
                            "workspace_id": str(c.workspace_id),
                        },
                    ))

        if updated_overdue + updated_at_risk > 0:
            session.commit()

    # Celery worker publishes alerts directly to Redis (never writes back to Outbox for notifications)
    for channel, event_type, alert_payload in pending_alerts:
        try:
            publish_event_sync(channel, event_type, alert_payload)
        except Exception as alert_err:
            logger.warning(f"[Celery Worker] Failed to publish deadline alert to Redis: {alert_err}")

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
