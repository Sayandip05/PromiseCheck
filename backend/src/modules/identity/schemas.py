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
