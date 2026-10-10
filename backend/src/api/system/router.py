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


from jobs.celery_stats import _query_celery_stats, query_celery_stats


@router.get("/status", response_model=OperationalStatusResponse)
async def get_operations_status():
    """Retrieve real-time operational queue and worker status from Celery."""
    stats = _query_celery_stats()
    return OperationalStatusResponse(
        queue_depth=stats["queue_depth"],
        active_workers=stats["active_workers"],
        system_status="operational",
    )


from fastapi.responses import PlainTextResponse
from core.metrics import metrics


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics() -> PlainTextResponse:
    """Export standard Prometheus exposition format (version 0.0.4)."""
    return PlainTextResponse(
        content=metrics.generate_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
