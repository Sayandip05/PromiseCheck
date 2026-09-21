"""Real-time Server-Sent Events (SSE) gateway powered by Redis Pub/Sub."""

import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logging import get_logger
from core.redis import publish_event, set_with_ttl, get_value, subscribe_channel
from core.security import decode_token
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

logger = get_logger("realtime_gateway")
router = APIRouter(prefix="/events", tags=["Real-time Events (SSE & Pub/Sub)"])


@router.get("/stream")
async def sse_event_stream(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for browser EventSource"),
    last_event_id: Optional[str] = Query(None, alias="last_event_id", description="Last received event ID for stream replay"),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) endpoint subscribing to workspace Redis events with Stream durability."""
    # Authenticate token from query param (EventSource standard) or Authorization header
    auth_header = request.headers.get("Authorization")
    raw_token = token or (auth_header.split(" ")[1] if auth_header and " " in auth_header else None)
    reconnect_last_id = request.headers.get("Last-Event-ID") or last_event_id

    workspace_id: uuid.UUID
    if raw_token:
        try:
            payload = decode_token(raw_token, expected_type="access")
            user_id = uuid.UUID(payload["sub"])
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            workspace_id = await get_active_workspace_id(db, user)
        except Exception:
            workspace_id = await get_active_workspace_id(db, None)
    else:
        workspace_id = await get_active_workspace_id(db, None)

    channel_name = f"ws:{workspace_id}:events"
    logger.info(f"Opening SSE connection for workspace {workspace_id} on channel '{channel_name}'")

    async def event_generator() -> AsyncGenerator[str, None]:
        # Initial handshake message
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'workspace_id': str(workspace_id)})}\n\n"

        # Replay any missed events from Redis Stream if reconnecting
        if reconnect_last_id:
            try:
                from core.redis import read_stream_events
                missed_events = await read_stream_events(channel_name, last_id=reconnect_last_id, count=50)
                for mev in missed_events:
                    m_id = mev.get("id", "")
                    m_type = mev.get("type", "message")
                    m_payload = mev.get("payload", {})
                    id_line = f"id: {m_id}\n" if m_id else ""
                    yield f"{id_line}event: {m_type}\ndata: {json.dumps(m_payload)}\n\n"
            except Exception as stream_err:
                logger.warning(f"Failed to replay stream events from '{reconnect_last_id}': {stream_err}")

        # Background listener queue
        queue: asyncio.Queue = asyncio.Queue()

        async def redis_listener():
            try:
                async for event in subscribe_channel(channel_name):
                    await queue.put(event)
            except Exception as e:
                logger.warning(f"SSE Redis listener error: {e}")

        # Start redis subscriber task
        listener_task = asyncio.create_task(redis_listener())

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info("Client closed SSE connection")
                    break

                try:
                    # Wait up to 15 seconds for an event from the Redis subscriber
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event.get("type", "message")
                    payload = event.get("payload", {})
                    msg_id = event.get("id", "")
                    id_line = f"id: {msg_id}\n" if msg_id else ""
                    yield f"{id_line}event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep HTTP/2 and reverse proxies alive
                    yield ": ping\n\n"

        finally:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/test-publish")
async def test_publish_event(
    event_type: str = "TEST_EVENT",
    message: str = "Test real-time message",
    db: AsyncSession = Depends(get_db),
):
    """Test utility to publish a message into Redis Pub/Sub."""
    workspace_id = await get_active_workspace_id(db, None)
    receivers = await publish_event(
        f"ws:{workspace_id}:events",
        event_type,
        {"message": message, "workspace_id": str(workspace_id)},
    )
    # Also test TTL key set
    await set_with_ttl(f"test:ping:{uuid.uuid4().hex[:6]}", {"msg": message}, ttl_seconds=60)
    return {"status": "published", "receivers": receivers, "channel": f"ws:{workspace_id}:events"}
