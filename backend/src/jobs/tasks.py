"""Shared background asynchronous tasks registered on the unified Celery app."""

from core.logging import get_logger
from jobs.celery_app import celery_app

logger = get_logger("celery_tasks")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ingestion_event(self, event_id: str) -> dict[str, str]:
    """Process an accepted provider ingestion event."""
    logger.info("Processing ingestion event", extra={"event_id": event_id})
    return {"status": "processed", "event_id": event_id}


@celery_app.task(bind=True, max_retries=2)
def scan_commitment_deadlines(self) -> dict[str, str]:
    """Periodic job scanning for commitments approaching deadline or in conflict."""
    logger.info("Running periodic commitment deadline risk evaluation")
    return {"status": "completed"}
