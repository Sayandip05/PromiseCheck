"""Integration tests for Celery priority queues, Redis Streams durability, and scheduler locks."""

import uuid
import pytest
from core.redis import get_async_redis, publish_event, read_stream_events, set_with_ttl_sync, get_sync_redis
from jobs.celery_app import celery_app
from jobs.tasks import (
    cleanup_expired_tokens,
    process_transcript_ingestion,
    scan_commitment_deadlines,
)


def test_celery_priority_queues_and_routing():
    """Verify that Celery priority queues (high_priority, default, ingestion) and routing rules are configured."""
    queue_names = {q.name for q in celery_app.conf.task_queues}
    assert "high_priority" in queue_names
    assert "default" in queue_names
    assert "ingestion" in queue_names

    routes = celery_app.conf.task_routes
    assert routes.get("jobs.tasks.process_transcript_ingestion", {}).get("queue") == "ingestion"
    assert routes.get("jobs.tasks.scan_commitment_deadlines", {}).get("queue") == "high_priority"
    assert routes.get("jobs.tasks.cleanup_expired_tokens", {}).get("queue") == "default"

    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.task_acks_late is True


@pytest.mark.asyncio
async def test_redis_streams_persistence_without_active_subscribers():
    """Verify that events are durably persisted to Redis Streams even if no subscriber is active."""
    try:
        r = get_async_redis()
        await r.ping()
    except Exception:
        pytest.skip("Redis not reachable; skipping live stream test.")

    test_channel = f"ws:test-stream-{uuid.uuid4().hex[:6]}:events"
    event_payload = {"commitment_id": str(uuid.uuid4()), "status": "overdue"}

    # Publish without any active SSE / PubSub listener
    receivers = await publish_event(test_channel, "COMMITMENT_OVERDUE", event_payload)
    # Even if receivers == 0, the message must be in the stream
    assert receivers >= 0

    # Read from the persistent stream
    stream_events = await read_stream_events(test_channel, last_id="0-0")
    assert len(stream_events) >= 1

    last_event = stream_events[-1]
    assert last_event["type"] == "COMMITMENT_OVERDUE"
    assert last_event["payload"]["commitment_id"] == event_payload["commitment_id"]
    assert "id" in last_event

    # Replaying with the returned id should yield 0 new events
    replay_after = await read_stream_events(test_channel, last_id=last_event["id"])
    assert len(replay_after) == 0


def test_job_state_24h_ttl_consistency():
    """Verify that job state writes use a consistent 86400s (24-hour) TTL."""
    try:
        sync_r = get_sync_redis()
        sync_r.ping()
    except Exception:
        pytest.skip("Redis not reachable; skipping TTL test.")

    test_job_id = f"job-test-{uuid.uuid4().hex[:6]}"
    set_with_ttl_sync(f"job:{test_job_id}", {"status": "processing"}, ttl_seconds=86400)

    ttl = sync_r.ttl(f"job:{test_job_id}")
    # TTL should be within 24 hours (~86400s)
    assert 86300 <= ttl <= 86400


def test_distributed_scheduler_lock_deduplication():
    """Verify that scan_commitment_deadlines skips duplicate execution when distributed lock is held."""
    try:
        sync_r = get_sync_redis()
        sync_r.ping()
    except Exception:
        pytest.skip("Redis not reachable; skipping lock test.")

    lock_key = "lock:celery_beat:scan_deadlines"
    # Acquire lock manually to simulate another running instance
    sync_r.set(lock_key, "worker-node-1", ex=60)

    # Temporarily set eager to False to test distributed lock behavior
    orig_eager = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = False

    try:
        res = scan_commitment_deadlines()
        assert res.get("status") == "skipped"
        assert res.get("reason") == "distributed_lock_held"
    finally:
        celery_app.conf.task_always_eager = orig_eager
        sync_r.delete(lock_key)
