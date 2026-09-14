"""Production-grade JWT identity and authentication routes."""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import get_current_user
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
    """Authenticate or register via Google OAuth / OIDC credential exchange."""
    import jwt

    email = payload.email
    full_name = payload.full_name or ""
    google_sub = ""

    # Parse Google credential JWT if passed from Google Identity Services (GIS)
    token_str = payload.credential or payload.id_token
    if token_str:
        try:
            unverified = jwt.decode(token_str, options={"verify_signature": False})
            email = email or unverified.get("email")
            full_name = full_name or unverified.get("name") or ""
            google_sub = unverified.get("sub") or ""
        except Exception:
            pass

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google credential or valid email required.",
        )

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
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token and clear all auth cookies."""
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or cookie_refresh
    if raw_token:
        await AuthService.revoke_refresh_token(db, raw_token)
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
