"""Audit trail router with compliance tracking and timeline events."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.audit.models import AuditEvent
from modules.audit.schemas import AuditEventDTO
from modules.iam import User, get_active_workspace_id, get_current_user

router = APIRouter(prefix="/audit", tags=["Audit & Compliance"])


@router.get("", response_model=list[AuditEventDTO])
async def list_audit_events(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of audit events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip for pagination"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve immutable audit and compliance trail for the workspace. Pure, idempotent read."""
    ws_id = await get_active_workspace_id(db, user)

    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == ws_id)
        .order_by(desc(AuditEvent.created_at))
        .offset(offset)
        .limit(limit)
    )
    events = res.scalars().all()

    return [
        AuditEventDTO(
            id=str(e.id),
            workspace_id=str(e.workspace_id),
            action=e.action,
            target_type=e.target_type,
            target_id=e.target_id,
            description=e.description or f"{e.action} on {e.target_type}",
            source=(e.payload or {}).get("source", "System"),
            timeAgo=(e.payload or {}).get("timeAgo", "Recently"),
            created_at=e.created_at,
            payload=e.payload or {},
        )
        for e in events
    ]
