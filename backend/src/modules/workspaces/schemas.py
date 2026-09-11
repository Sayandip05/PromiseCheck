"""Workspaces module schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core.security import Role


class WorkspaceCreateRequest(BaseModel):
    """Payload to provision a new workspace."""

    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50)


class WorkspaceResponse(BaseModel):
    """Public workspace profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class MembershipResponse(BaseModel):
    """Membership details with assigned role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: Role
    created_at: datetime


class InvitationRequest(BaseModel):
    """Payload to invite a teammate."""

    email: str = Field(min_length=3)
    role: Role = Role.MEMBER
