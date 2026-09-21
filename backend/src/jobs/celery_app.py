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

from kombu import Exchange, Queue

_default_exchange = Exchange("default", type="direct")
_high_priority_exchange = Exchange("high_priority", type="direct")
_ingestion_exchange = Exchange("ingestion", type="direct")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DEFAULT_TIMEZONE or "UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Multi-queue priority configuration
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_queues=(
        Queue("high_priority", _high_priority_exchange, routing_key="high_priority"),
        Queue("default", _default_exchange, routing_key="default"),
        Queue("ingestion", _ingestion_exchange, routing_key="ingestion"),
    ),
    task_routes={
        "jobs.tasks.scan_commitment_deadlines": {"queue": "high_priority"},
        "jobs.tasks.dispatch_notification_alert": {"queue": "high_priority"},
        "jobs.tasks.process_transcript_ingestion": {"queue": "ingestion"},
        "jobs.tasks.cleanup_expired_tokens": {"queue": "default"},
    },
    # Redis TTL Configuration for task results
    result_expires=86400,  # Expire task results after 24 hours (automatic TTL cleanup)
    result_backend_transport_options={"global_keyprefix": "promisecheck:celery:result:"},
    broker_transport_options={"visibility_timeout": 3600},
    beat_schedule={
        "periodic-commitment-risk-scan": {
            "task": "jobs.tasks.scan_commitment_deadlines",
            "schedule": 3600.0,  # Runs every hour to check delivery deadlines and risks
        },
        # Nightly token cleanup — runs at 03:00 UTC every day.
        # Uses LIMIT-batched deletes to avoid a single large DELETE causing
        # table-level pressure or autovacuum storms on the refresh_tokens table.
        "nightly-expired-token-cleanup": {
            "task": "jobs.tasks.cleanup_expired_tokens",
            "schedule": 86400.0,  # Once per day
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
