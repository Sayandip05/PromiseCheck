"""Integration tests for Redis Pub/Sub event streaming, TTL keys, and Celery background workers."""

import asyncio
import uuid
import pytest

from core.redis import (
    get_async_redis,
    publish_event,
    set_with_ttl,
    get_value,
    delete_key,
    subscribe_channel,
)
from jobs.celery_app import check_redis_health
from jobs.tasks import scan_commitment_deadlines


async def _is_redis_reachable() -> bool:
    try:
        client = get_async_redis()
        pong = await client.ping()
        return bool(pong)
    except Exception:
        return False


@pytest.mark.asyncio
async def test_redis_graceful_offline_resilience():
    """Verify that Redis operations never crash the application when Redis is offline."""
    test_key = f"test:offline:{uuid.uuid4().hex[:8]}"
    test_channel = f"ws:offline-{uuid.uuid4().hex[:6]}:events"

    # If Redis is offline, these should safely return False/0/None without throwing unhandled exceptions
    is_live = await _is_redis_reachable()
    if not is_live:
        success = await set_with_ttl(test_key, {"status": "test"}, ttl_seconds=60)
        assert success is False
        val = await get_value(test_key)
        assert val is None
        receivers = await publish_event(test_channel, "ALERT", {"msg": "test"})
        assert receivers == 0
    else:
        # Live Redis test
        success = await set_with_ttl(test_key, {"status": "test"}, ttl_seconds=60)
        assert success is True
        val = await get_value(test_key)
        assert val == {"status": "test"}
        await delete_key(test_key)


@pytest.mark.asyncio
async def test_redis_live_pubsub_and_ttl():
    """Verify live Redis Pub/Sub and TTL when Redis is reachable."""
    is_live = await _is_redis_reachable()
    if not is_live:
        pytest.skip("Local Redis daemon is offline; skipped live socket pubsub test.")

    redis_client = get_async_redis()
    test_key = f"test:cache:{uuid.uuid4().hex[:8]}"
    test_payload = {"commitment_id": "comm-123", "status": "on-track"}

    # Set with TTL
    await set_with_ttl(test_key, test_payload, ttl_seconds=60)
    retrieved = await get_value(test_key)
    assert retrieved == test_payload
    ttl = await redis_client.ttl(test_key)
    assert 0 < ttl <= 60
    await delete_key(test_key)

    # PubSub broadcast
    test_channel = f"ws:test-{uuid.uuid4().hex[:6]}:events"
    received_messages: list[dict] = []

    async def listener():
        async for msg in subscribe_channel(test_channel):
            received_messages.append(msg)
            break

    listen_task = asyncio.create_task(listener())
    await asyncio.sleep(0.05)

    receivers = await publish_event(test_channel, "TEST_ALERT", {"title": "SSO Delivery"})
    assert receivers >= 0

    try:
        await asyncio.wait_for(listen_task, timeout=2.0)
    except asyncio.TimeoutError:
        listen_task.cancel()

    assert len(received_messages) >= 1


def test_celery_task_definitions():
    """Verify that Celery task definitions run correctly and return status."""
    res = scan_commitment_deadlines()
    assert isinstance(res, dict)
    assert res.get("status") == "completed"
