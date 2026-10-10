"""Centralized security, cryptography, Bcrypt hashing, and JWT authentication."""

import hashlib
import hmac
import math
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer

from core.config import settings
from core.logging import get_logger

bearer_scheme = HTTPBearer(auto_error=False)
logger = get_logger("security")


def _get_jwt_secret() -> str:
    """Retrieve JWT signing secret from environment or settings.

    SECURITY: No fallback. If none of JWT_SECRET_KEY, SECRET_KEY, or
    SESSION_SIGNING_KEY are set, startup crashes immediately with a clear
    error. This prevents misconfigured deployments from silently using a
    publicly-known development key.
    """
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
        raise RuntimeError(
            "JWT signing secret is not configured. "
            "Set JWT_SECRET_KEY, SECRET_KEY, or SESSION_SIGNING_KEY in your environment. "
            "This is a required secret — the application cannot start without it."
        )
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


async def blacklist_access_token(token: str) -> bool:
    """Store the JTI of an active access token in Redis with its remaining TTL.

    Fix #12: Called on logout to ensure the access token cannot be replayed
    after the session is revoked. The Redis key auto-expires at the token's
    natural expiry so no cleanup is required.
    Returns True if blacklisted, False if token already expired or invalid.
    """
    from core.redis import get_async_redis
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[settings.JWT_ALGORITHM],
        )
        jti = payload.get("jti")
        exp = payload.get("exp", 0)
        if not jti:
            return False  # No JTI claim — cannot blacklist
        remaining_ttl = max(1, math.ceil(exp - datetime.now(timezone.utc).timestamp()))
        await get_async_redis().set(f"blocklist:jti:{jti}", "1", ex=remaining_ttl)
        logger.info(f"Access token JTI {jti[:8]}... blacklisted (TTL={remaining_ttl}s)")
        return True
    except jwt.ExpiredSignatureError:
        return False  # Already expired — no need to blacklist
    except Exception as exc:
        logger.warning(f"Failed to blacklist access token: {exc}")
        return False


async def check_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is in the Redis blocklist. Returns True if revoked.

    SECURITY TRADE-OFF (intentional fail-open):
    If Redis is unavailable, we return False (token is NOT blacklisted) rather
    than True (rejecting all requests). This is a deliberate availability vs.
    security trade-off:
    - Failing closed (return True): blocks every authenticated user when Redis
      drops, causing a complete service outage.
    - Failing open (return False): allows a narrow replay window for explicitly
      logged-out tokens until Redis recovers. This window is bounded by the
      access token TTL (15 minutes max).
    The warning log below is the alert signal — wire it to PagerDuty/Alertmanager
    so Redis downtime is detected immediately.
    """
    from core.redis import get_async_redis
    try:
        return bool(await get_async_redis().exists(f"blocklist:jti:{jti}"))
    except Exception as exc:
        # ALERT: Redis blocklist unavailable — fail-open is intentional (see docstring).
        # If this warning fires repeatedly, Redis is down and the on-call team should act.
        logger.warning(
            f"[SECURITY ALERT] Token blocklist Redis check failed (failing open). "
            f"Revoked tokens may replay until Redis recovers. Error: {exc}"
        )
        return False  # Intentional: availability over strict revocation during Redis outage



