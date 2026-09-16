"""Single shared Celery application for background workers and beat scheduler."""

import os
import redis.asyncio as aioredis
from celery import Celery

from core.config import settings

_redis_url = settings.REDIS_URL or os.getenv("REDIS_URL") or "redis://127.0.0.1:6379/0"

celery_app = Celery(
    "promisecheck",
    broker=_redis_url,
    backend=_redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DEFAULT_TIMEZONE or "UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Redis TTL Configuration for task results
    result_expires=86400,  # Expire task results after 24 hours (automatic TTL cleanup)
    result_backend_transport_options={"global_keyprefix": "promisecheck:celery:result:"},
    broker_transport_options={"visibility_timeout": 3600},
    beat_schedule={
        "periodic-commitment-risk-scan": {
            "task": "jobs.tasks.scan_commitment_deadlines",
            "schedule": 3600.0,  # Runs every hour to check delivery deadlines and risks
        },
    },
)


async def check_redis_health() -> tuple[bool, str]:
    """Verify Redis connection for readiness probe."""
    try:
        client = aioredis.from_url(_redis_url, socket_timeout=3.0)
        pong = await client.ping()
        await client.aclose()
        if pong:
            return True, "connected"
        return False, "unexpected ping response"
    except Exception as exc:
        return False, str(exc)
