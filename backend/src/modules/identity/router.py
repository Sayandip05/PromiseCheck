"""Identity and authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import extract_session_token, hash_token
from modules.identity.schemas import UserLoginRequest, UserRegisterRequest, UserResponse
from modules.identity.service import AuthService

router = APIRouter(prefix="/auth", tags=["Identity & Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    """Register a new account and establish a session."""
    try:
        user, raw_token = await AuthService.register_user(db, payload)
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=raw_token,
            max_age=settings.SESSION_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
            secure=settings.APP_ENV == "production",
        )
        return user
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/login", response_model=UserResponse)
async def login(payload: UserLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate and create server-side session."""
    try:
        user, raw_token = await AuthService.authenticate(db, payload.email, payload.password)
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=raw_token,
            max_age=settings.SESSION_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
            secure=settings.APP_ENV == "production",
        )
        return user
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    token: str = Depends(extract_session_token),
    db: AsyncSession = Depends(get_db),
):
    """Revoke active session and clear cookie."""
    token_hash = hash_token(token)
    await AuthService.revoke_session(db, token_hash)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return {"status": "logged_out"}
