"""Audit trail router with compliance tracking and timeline events."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from modules.audit.models import AuditEvent
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/audit", tags=["Audit & Compliance"])


class AuditEventDTO(BaseModel):
    """Audit log entry DTO matching frontend activity and compliance views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    action: str
    target_type: str
    target_id: str
    description: str
    source: str
    timeAgo: str
    created_at: datetime
    payload: dict[str, Any] = {}


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
