"""Operations, system status, and maintenance router."""

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/operations", tags=["Operations"])
logger = logging.getLogger("operations")


class OperationalStatusResponse(BaseModel):
    """System operational metrics and background queue status."""

    queue_depth: int = 0
    active_workers: int = 0
    system_status: str = "operational"


def _query_celery_stats() -> dict[str, Any]:
    """Return real-time Celery inspector stats without crashing on failure.

    Uses ``celery inspect`` which talks to workers via the Redis broker.
    Falls back to safe defaults if the broker is unreachable or no workers
    are online — this keeps the endpoint non-blocking and safe for health checks.
    """
    try:
        from jobs.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=1.5)
        # active() returns {worker_name: [task, ...], ...} or None
        active: dict | None = inspector.active()
        if active is None:
            return {"queue_depth": 0, "active_workers": 0}

        active_workers = len(active)
        queue_depth = sum(len(tasks) for tasks in active.values())
        return {"queue_depth": queue_depth, "active_workers": active_workers}
    except Exception as exc:
        logger.warning(f"[ops] Celery inspect failed: {exc}")
        return {"queue_depth": 0, "active_workers": 0}


@router.get("/status", response_model=OperationalStatusResponse)
async def get_operations_status():
    """Retrieve real-time operational queue and worker status from Celery."""
    stats = _query_celery_stats()
    return OperationalStatusResponse(
        queue_depth=stats["queue_depth"],
        active_workers=stats["active_workers"],
        system_status="operational",
    )
