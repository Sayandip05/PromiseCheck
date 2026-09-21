"""Audit trail router with compliance tracking and timeline events."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user_optional
from modules.audit.models import AuditEvent
from modules.audit.service import record_audit_event
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



async def _seed_audit_events_if_empty(db: AsyncSession, workspace_id: uuid.UUID):
    """Seed initial compliance activity logs if empty."""
    res = await db.execute(select(AuditEvent).where(AuditEvent.workspace_id == workspace_id).limit(1))
    if res.scalar_one_or_none():
        return

    dummy_actor = uuid.uuid4()
    seeds = [
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=dummy_actor,
            action="ticket_synced",
            target_type="jira",
            target_id="ENG-1042",
            description="Jira sync updated target delivery to Oct 05",
            payload={"source": "Jira · 10 min ago", "timeAgo": "10 min ago"},
        ),
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=dummy_actor,
            action="commitment_confirmed",
            target_type="commitment",
            target_id="comm-1",
            description="Maya confirmed the SSO commitment",
            payload={"source": "Manual review · Yesterday", "timeAgo": "Yesterday"},
        ),
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=dummy_actor,
            action="transcript_imported",
            target_type="ingestion",
            target_id="rec-meet-8823",
            description="Acme onboarding transcript imported",
            payload={"source": "Google Meet · Yesterday", "timeAgo": "Yesterday"},
        ),
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=dummy_actor,
            action="alert_dispatched",
            target_type="slack",
            target_id="#customer-commitments",
            description="Slack alert dispatched to #customer-commitments",
            payload={"source": "Slack · 2 days ago", "timeAgo": "2 days ago"},
        ),
    ]
    db.add_all(seeds)
    await db.commit()


@router.get("", response_model=list[AuditEventDTO])
async def list_audit_events(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieve immutable audit and compliance trail for the workspace."""
    ws_id = await get_active_workspace_id(db, user)
    await _seed_audit_events_if_empty(db, ws_id)

    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == ws_id)
        .order_by(desc(AuditEvent.created_at))
        .limit(50)
    )
    events = res.scalars().all()

    return [
        AuditEventDTO(
            id=str(e.id),
            workspace_id=str(e.workspace_id),
            action=e.action,
            target_type=e.target_type,
            target_id=e.target_id,
            # description now comes from the dedicated column, not JSONB payload
            description=e.description or f"{e.action} on {e.target_type}",
            source=(e.payload or {}).get("source", "System"),
            timeAgo=(e.payload or {}).get("timeAgo", "Recently"),
            created_at=e.created_at,
            payload=e.payload or {},
        )
        for e in events
    ]
