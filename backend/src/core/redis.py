"""Centralized Redis client, Pub/Sub event bus, and TTL key manager."""

import asyncio
import json
import os
from typing import Any, AsyncGenerator, Optional

import redis
import redis.asyncio as aioredis

from core.config import settings
from core.logging import get_logger

logger = get_logger("redis_service")

# Resolve Redis URL strictly from settings or environment
REDIS_URL = settings.REDIS_URL or os.getenv("REDIS_URL") or "redis://127.0.0.1:6379/0"

# Async Redis client pool & associated loop
_async_redis_client: Optional[aioredis.Redis] = None
_async_redis_loop: Optional[asyncio.AbstractEventLoop] = None

# Synchronous Redis client for Celery tasks
_sync_redis_client: Optional[redis.Redis] = None


def get_sync_redis() -> redis.Redis:
    """Retrieve or initialize synchronous Redis connection for background worker jobs."""
    global _sync_redis_client
    if _sync_redis_client is None:
        _sync_redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
    return _sync_redis_client


def get_async_redis() -> aioredis.Redis:
    """Retrieve or initialize async Redis client for FastAPI request loop."""
    global _async_redis_client, _async_redis_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _async_redis_client is None or _async_redis_loop != current_loop:
        _async_redis_client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        _async_redis_loop = current_loop
    return _async_redis_client


# ==============================================================================
# 1. TTL Key-Value Utilities
# ==============================================================================


async def set_with_ttl(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Set a string or JSON-serializable value with an automatic expiration TTL."""
    try:
        client = get_async_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await client.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning(f"Redis set_with_ttl failed for key '{key}': {exc}")
        return False


def set_with_ttl_sync(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Synchronous version of set_with_ttl for Celery worker tasks."""
    try:
        client = get_sync_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        client.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning(f"Redis sync set_with_ttl failed for key '{key}': {exc}")
        return False


async def get_value(key: str) -> Optional[Any]:
    """Retrieve a value by key from Redis."""
    try:
        client = get_async_redis()
        val = await client.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    except Exception as exc:
        logger.warning(f"Redis get_value failed for key '{key}': {exc}")
        return None


async def delete_key(key: str) -> bool:
    """Delete a key from Redis."""
    try:
        client = get_async_redis()
        await client.delete(key)
        return True
    except Exception as exc:
        logger.warning(f"Redis delete_key failed for key '{key}': {exc}")
        return False


# ==============================================================================
# 2. Redis Pub/Sub Event Bus
# ==============================================================================


async def publish_event(channel: str, event_type: str, data: dict[str, Any]) -> int:
    """Publish an event to a Redis Pub/Sub channel and append to persistent Redis Stream."""
    message = json.dumps({
        "type": event_type,
        "payload": data,
    }, default=str)
    receivers = 0
    try:
        client = get_async_redis()
        receivers = await client.publish(channel, message)
        # Durable Redis Stream append: messages survive subscriber disconnections
        stream_key = f"stream:{channel}"
        stream_fields = {
            "type": event_type,
            "payload": json.dumps(data, default=str),
        }
        await client.xadd(stream_key, stream_fields, maxlen=1000, approximate=True)
        logger.info(f"Published event '{event_type}' to channel '{channel}' ({receivers} subscribers, stream appended)")
    except Exception as exc:
        logger.warning(f"Redis publish_event failed for channel '{channel}': {exc}")
    return receivers


def publish_event_sync(channel: str, event_type: str, data: dict[str, Any]) -> int:
    """Synchronous version of publish_event for Celery background tasks."""
    message = json.dumps({
        "type": event_type,
        "payload": data,
    }, default=str)
    receivers = 0
    try:
        client = get_sync_redis()
        receivers = client.publish(channel, message)
        stream_key = f"stream:{channel}"
        stream_fields = {
            "type": event_type,
            "payload": json.dumps(data, default=str),
        }
        client.xadd(stream_key, stream_fields, maxlen=1000, approximate=True)
        logger.info(f"[Celery Worker] Published event '{event_type}' to channel '{channel}' ({receivers} subscribers, stream appended)")
    except Exception as exc:
        logger.warning(f"Redis sync publish_event failed for channel '{channel}': {exc}")
    return receivers


async def read_stream_events(
    channel: str,
    last_id: str = "0-0",
    count: int = 50,
) -> list[dict[str, Any]]:
    """Read persistent events from a Redis Stream for client replay on reconnection."""
    stream_key = f"stream:{channel}"
    events: list[dict[str, Any]] = []
    try:
        client = get_async_redis()
        # Read events strictly newer than last_id
        res = await client.xread({stream_key: last_id}, count=count)
        if res:
            for _, entries in res:
                for entry_id, fields in entries:
                    event_type = fields.get("type", "message")
                    raw_payload = fields.get("payload", "{}")
                    try:
                        payload = json.loads(raw_payload)
                    except (json.JSONDecodeError, TypeError):
                        payload = raw_payload
                    events.append({
                        "id": entry_id,
                        "type": event_type,
                        "payload": payload,
                    })
    except Exception as exc:
        logger.warning(f"Redis read_stream_events failed for '{stream_key}': {exc}")
    return events


async def subscribe_channel(channel: str) -> AsyncGenerator[dict[str, Any], None]:
    """Async generator subscribing to a Redis channel and yielding parsed event dicts.

    Fix #5: Creates a DEDICATED Redis connection per subscriber instead of
    reusing the shared singleton pool. Redis Pub/Sub holds a connection open for
    the entire lifetime of the subscription. If the shared pool were used here,
    1,000 concurrent SSE connections would exhaust the pool and block all other
    Redis operations (rate limiting, TTL writes, event publishing).

    The dedicated connection is fully closed in the `finally` block regardless
    of how the generator exits (client disconnect, error, cancellation).
    """
    # Each subscriber gets its own isolated connection — never competes with the pool
    dedicated_client = aioredis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )
    pubsub = dedicated_client.pubsub()
    await pubsub.subscribe(channel)
    logger.info(f"Subscribed to Redis channel: {channel} (dedicated connection)")

    try:
        async for message in pubsub.listen():
            if message and message.get("type") == "message":
                raw_data = message.get("data")
                try:
                    parsed = json.loads(raw_data)
                    yield parsed
                except (json.JSONDecodeError, TypeError):
                    yield {"type": "raw", "payload": raw_data}
    except Exception as exc:
        logger.error(f"Error in Redis pubsub listener on '{channel}': {exc}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await dedicated_client.aclose()  # fully release the dedicated connection
        logger.info(f"Unsubscribed and closed Redis pubsub channel: {channel}")

