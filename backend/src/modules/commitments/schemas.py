"""Commitments schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommitmentCreateRequest(BaseModel):
    """Payload to record a confirmed promise."""

    title: str
    quote: str
    customer_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    due_date: datetime | None = None


class CommitmentResponse(BaseModel):
    """Commitment summary response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    quote: str
    status: str
    due_date: datetime | None = None
    created_at: datetime
