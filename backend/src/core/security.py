"""Centralized security, cryptography, Bcrypt hashing, and JWT authentication."""

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import Cookie, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _get_jwt_secret() -> str:
    """Retrieve signing secret strictly from environment/settings with fallback."""
    key = (
        settings.JWT_SECRET_KEY
        or os.getenv("JWT_SECRET_KEY")
        or settings.SECRET_KEY
        or os.getenv("SECRET_KEY")
        or settings.SESSION_SIGNING_KEY
        or os.getenv("SESSION_SIGNING_KEY")
        or ""
    )
    if not key:
        key = "dev-insecure-jwt-secret-key-change-me-32chars"
    return key


class Role(str, Enum):
    """Workspace membership roles."""

    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random token string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute SHA-256 digest of a sensitive token before persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Hash password using standard Bcrypt with salt rounds = 12."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored Bcrypt hash (with PBKDF2 backwards compatibility)."""
    if not hashed_password:
        return False

    # Backwards compatibility with PBKDF2 hashes if any exist
    if "$" in hashed_password and not hashed_password.startswith("$2"):
        try:
            salt_hex, key_hex = hashed_password.split("$")
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)
            actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
            return hmac.compare_digest(actual_key, expected_key)
        except Exception:
            return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    user_id: str | uuid.UUID,
    email: str,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create short-lived JWT access token for stateless API authorization."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str | uuid.UUID,
    family_id: Optional[str] = None,
) -> tuple[str, str, str, datetime]:
    """Generate rotating refresh token JWT. Returns (raw_token, jti, family_id, expires_at)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = secrets.token_hex(16)
    token_family = family_id or secrets.token_hex(16)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "family_id": token_family,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, _get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)
    return token, jti, token_family, expires_at


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and cryptographically verify a JWT signature, expiration, and token type."""
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type: expected '{expected_type}'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


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
):
    """FastAPI dependency: stateless JWT token resolution and user profile fetch."""
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

    from core.database import AsyncSessionLocal
    from modules.identity.models import User

    async with AsyncSessionLocal() as db:
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
) -> Optional[Any]:
    """Optional authentication resolution returning User or None."""
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_uuid = uuid.UUID(user_id_str)
        from core.database import AsyncSessionLocal
        from modules.identity.models import User

        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_uuid)
            if user and user.is_active:
                return user
            return None
    except Exception:
        return None

