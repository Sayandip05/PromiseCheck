"""Production-grade JWT identity and authentication routes."""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import (
    bearer_scheme,
    blacklist_access_token,
    get_current_user,
)
from modules.identity.models import User
from modules.identity.schemas import (
    GoogleAuthRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserMeResponse,
    UserRegisterRequest,
    UserResponse,
)
from modules.identity.service import AuthService

router = APIRouter(prefix="/auth", tags=["Identity & Auth"])


def _set_token_cookies(response: Response, access_token: str, refresh_token: str, expires_in: int):
    """Set secure HttpOnly cookies for refresh token and access token."""
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE or settings.APP_ENV == "production",
        path="/",
    )
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=expires_in,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE or settings.APP_ENV == "production",
        path="/",
    )


def _clear_token_cookies(response: Response):
    """Clear all authentication cookies."""
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.ACCESS_COOKIE_NAME, path="/")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with Bcrypt password hashing, returning JWT access & refresh tokens."""
    user, access_token, refresh_token, expires_in, active_ws, all_ws = (
        await AuthService.register_user(db, payload)
    )
    _set_token_cookies(response, access_token, refresh_token, expires_in)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
        active_workspace=active_ws,
        workspaces=all_ws,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password via Bcrypt, issuing JWT access & refresh tokens."""
    user, access_token, refresh_token, expires_in, active_ws, all_ws = (
        await AuthService.authenticate(db, payload.email, payload.password)
    )
    _set_token_cookies(response, access_token, refresh_token, expires_in)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
        active_workspace=active_ws,
        workspaces=all_ws,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    cookie_refresh: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token: issues a fresh Access Token and rotates the Refresh Token with reuse detection."""
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or cookie_refresh
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token in request body or cookie.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, new_access, new_refresh, expires_in, active_ws, all_ws = (
        await AuthService.refresh_token_pair(db, raw_token)
    )
    _set_token_cookies(response, new_access, new_refresh, expires_in)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
        active_workspace=active_ws,
        workspaces=all_ws,
    )


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    payload: GoogleAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate or register via Google OAuth / OIDC credential exchange.

    The Google credential JWT is cryptographically verified using google-auth:
    - RS256 signature verified against Google's public keys
    - Audience must match GOOGLE_CLIENT_ID
    - Token must not be expired
    Passes only if all checks succeed; raises 401 otherwise.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    token_str = payload.credential or payload.id_token
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google credential (id_token) is required.",
        )

    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured. GOOGLE_CLIENT_ID is not set.",
        )

    try:
        # verify_oauth2_token cryptographically verifies RS256 signature against Google JWKS,
        # audience matching client_id, issuer, and token expiration.
        id_info = google_id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credential: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = id_info.get("email")
    if not email or not id_info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is missing or unverified.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    full_name = id_info.get("name") or payload.full_name or ""
    google_sub = id_info.get("sub") or ""

    user, access_token, refresh_token, expires_in, active_ws, all_ws = (
        await AuthService.authenticate_google(
            db, email=email, full_name=full_name, google_sub=google_sub
        )
    )
    _set_token_cookies(response, access_token, refresh_token, expires_in)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
        active_workspace=active_ws,
        workspaces=all_ws,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    cookie_refresh: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    cookie_access: Optional[str] = Cookie(default=None, alias=settings.ACCESS_COOKIE_NAME),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token, blacklist access token, and clear all auth cookies.

    Fix #12: Extracts the current access token from Bearer header or cookie and
    blacklists its JTI in Redis with the remaining TTL. Any attempt to replay
    this token after logout will receive 401 'Token has been revoked'.
    """
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or cookie_refresh
    if raw_token:
        await AuthService.revoke_refresh_token(db, raw_token)

    # Blacklist the active access token so it cannot be replayed post-logout
    access_token = (bearer_auth.credentials if bearer_auth else None) or cookie_access
    if access_token:
        await blacklist_access_token(access_token)

    _clear_token_cookies(response)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stateless JWT authentication: returns user profile and workspace context."""
    active_ws, all_ws = await AuthService.get_user_workspaces(db, user.id)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        active_workspace=active_ws,
        workspaces=all_ws,
    )
