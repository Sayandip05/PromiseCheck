"""Single shared Celery application for background workers and beat scheduler."""

import redis.asyncio as aioredis
from celery import Celery

from core.config import settings

celery_app = Celery(
    "promisecheck",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DEFAULT_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Periodic reconciliation, deadline risk scans, and webhook subscription renewals
    },
)


async def check_redis_health() -> tuple[bool, str]:
    """Verify Redis connection for readiness probe."""
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=3.0)
        pong = await client.ping()
        await client.aclose()
        if pong:
            return True, "connected"
        return False, "unexpected ping response"
    except Exception as exc:
        return False, str(exc)
