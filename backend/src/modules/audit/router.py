"""Audit trail router."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/audit", tags=["Audit & Compliance"])


class AuditEventResponse(BaseModel):
    """Audit log entry."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    target_type: str
    target_id: str
    created_at: datetime


@router.get("", response_model=list[AuditEventResponse])
async def list_audit_events():
    """List workspace audit events."""
    return []
