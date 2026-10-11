"""Notifications Celery background dispatch tasks."""

from typing import Any

from core.logging import get_logger
from core.redis import publish_event_sync
from jobs.celery_app import celery_app

logger = get_logger("modules.notifications.tasks")


@celery_app.task(
    name="jobs.tasks.dispatch_notification_alert",
    bind=True,
    queue="high_priority",
    max_retries=3,
)
def dispatch_notification_alert(
    self,
    channel: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Async worker task to deliver deadline alerts to Redis and external notification sinks."""
    logger.info(f"[Celery Worker] Delivering notification alert '{event_type}' to channel '{channel}'")
    publish_event_sync(channel, event_type, payload)
