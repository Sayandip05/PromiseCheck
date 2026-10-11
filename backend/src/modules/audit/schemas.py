"""Audit domain Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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
