"""IAM authentication and authorization dependencies."""

import uuid
from typing import Any, Optional

from fastapi import Cookie, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import (
    Role,
    bearer_scheme,
    check_token_blacklisted,
    decode_token,
)
from modules.iam.models import Membership, User


def extract_access_token(
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    cookie_token: Optional[str] = Cookie(default=None, alias=settings.ACCESS_COOKIE_NAME),
) -> str:
    """Extract access token from Authorization Bearer header or fallback cookie."""
    if bearer_auth and bearer_auth.credentials:
        return bearer_auth.credentials
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Security(extract_access_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: stateless JWT token resolution and user profile fetch.

    Shares the request-scoped db session injected via Depends(get_db) to avoid
    opening multiple connections per request.
    Checks the JTI blocklist in Redis so revoked tokens are rejected.
    """
    payload = decode_token(token, expected_type="access")
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject tokens that were explicitly blacklisted on logout
    jti = payload.get("jti")
    if jti and await check_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_uuid)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def extract_access_token_optional(
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    cookie_token: Optional[str] = Cookie(default=None, alias=settings.ACCESS_COOKIE_NAME),
) -> Optional[str]:
    """Extract access token if present without raising 401."""
    if bearer_auth and bearer_auth.credentials:
        return bearer_auth.credentials
    if cookie_token:
        return cookie_token
    return None


async def get_current_user_optional(
    token: Optional[str] = Security(extract_access_token_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Optional authentication resolution returning User or None.

    Shares the request-scoped db session instead of opening its own AsyncSessionLocal().
    """
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_uuid = uuid.UUID(user_id_str)

        user = await db.get(User, user_uuid)
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


def require_role(min_role: Role):
    """FastAPI dependency enforcing a minimum RBAC role in the caller's active workspace.

    Hierarchy: VIEWER (1) < MEMBER (2) < MANAGER (3) < ADMIN (4)
    """
    role_levels = {
        Role.VIEWER: 1,
        Role.MEMBER: 2,
        Role.MANAGER: 3,
        Role.ADMIN: 4,
    }

    async def _role_guard(
        user: Any = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Any:
        stmt = select(Membership).where(Membership.user_id == user.id)
        res = await db.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no workspace membership",
            )
        current_level = role_levels.get(mem.role, 0)
        required_level = role_levels.get(min_role, 0)
        if current_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires at least {min_role.value} role",
            )
        return user

    return _role_guard
