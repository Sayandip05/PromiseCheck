"""Audit logging service for immutable compliance event logging."""

import uuid
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from modules.audit.models import AuditEvent


async def record_audit_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    target_type: str,
    target_id: str,
    description: str,
    payload: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    """Helper to append an immutable audit record.

    description is stored in the dedicated Text column (queryable via B-tree).
    payload holds only structured metadata — the description key is no longer
    duplicated there.
    """
    event = AuditEvent(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        description=description,
        payload=payload or {},
    )
    db.add(event)
    await db.flush()
    return event
