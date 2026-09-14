"""Identity module Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegisterRequest(BaseModel):
    """Payload to register a new local user."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class UserLoginRequest(BaseModel):
    """Payload to authenticate user."""

    email: str
    password: str


class UserResponse(BaseModel):
    """Public user identity representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class SessionResponse(BaseModel):
    """Active session metadata."""

    session_id: uuid.UUID
    user: UserResponse
    expires_at: datetime


class WorkspaceSummary(BaseModel):
    """Workspace summary for authenticated user context."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    role: str = "admin"


class UserMeResponse(BaseModel):
    """Authenticated user profile with workspace context."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    active_workspace: WorkspaceSummary | None = None
    workspaces: list[WorkspaceSummary] = []


class TokenResponse(BaseModel):
    """Production JWT token pair response with active user & workspace context."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # in seconds (e.g. 900 for 15m)
    user: UserResponse
    active_workspace: WorkspaceSummary | None = None
    workspaces: list[WorkspaceSummary] = []


class RefreshTokenRequest(BaseModel):
    """Payload to exchange a refresh token for new credentials."""

    refresh_token: str | None = None


class GoogleAuthRequest(BaseModel):
    """Google OAuth / OIDC credential exchange request."""

    credential: str | None = None
    id_token: str | None = None
    email: str | None = None
    full_name: str | None = None


