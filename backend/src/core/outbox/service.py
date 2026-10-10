"""Transactional Outbox domain service for durable intent persistence."""

import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.outbox.models import OutboxEvent


async def create_outbox_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Create and append an OutboxEvent row within the current active DB transaction.

    Ensures that intent is atomically committed alongside business entity changes.
    Never bypass this in HTTP handlers for heavy background work.
    """
    event = OutboxEvent(
        workspace_id=workspace_id,
        event_type=event_type,
        payload=payload,
        status="pending",
    )
    db.add(event)
    return event
