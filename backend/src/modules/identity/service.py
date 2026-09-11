"""Identity service for user authentication and session management."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import generate_secure_token, hash_password, hash_token, verify_password
from modules.identity.models import Session, User
from modules.identity.schemas import UserRegisterRequest


class AuthService:
    """Authentication and session lifecycle operations."""

    @staticmethod
    async def register_user(db: AsyncSession, payload: UserRegisterRequest) -> tuple[User, str]:
        """Register a new user and issue an initial session token."""
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise ValueError(f"User with email '{payload.email}' already exists.")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        await db.flush()

        raw_token = generate_secure_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS),
        )
        db.add(session)
        await db.commit()
        return user, raw_token

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> tuple[User, str]:
        """Authenticate credentials and generate a fresh session token."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password.")
        if not user.is_active:
            raise ValueError("Account is deactivated.")

        raw_token = generate_secure_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS),
        )
        db.add(session)
        await db.commit()
        return user, raw_token

    @staticmethod
    async def revoke_session(db: AsyncSession, token_hash_value: str) -> bool:
        """Revoke an active session by token hash."""
        result = await db.execute(select(Session).where(Session.token_hash == token_hash_value))
        session = result.scalar_one_or_none()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        return False
