"""Identity service for user authentication, Bcrypt hashing, and JWT token rotation."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.redis import delete_key, get_value, set_with_ttl
from core.security import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from modules.iam.models import Identity, Invitation, Membership, RefreshToken, User, Workspace
from modules.iam.schemas import (
    UserRegisterRequest,
    WorkspaceCreateRequest,
    WorkspaceSummary,
)
from core.logging import get_logger

logger = get_logger("identity_service")


class AuthService:
    """Authentication, Bcrypt verification, and JWT token pair lifecycle."""

    @staticmethod
    async def get_user_workspaces(
        db: AsyncSession, user_id: uuid.UUID
    ) -> tuple[WorkspaceSummary | None, list[WorkspaceSummary]]:
        """Retrieve workspace summary list and active workspace for a user."""
        res = await db.execute(
            select(Membership, Workspace)
            .join(Workspace, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user_id)
        )
        workspaces: list[WorkspaceSummary] = [
            WorkspaceSummary(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                role=mem.role.value if hasattr(mem.role, "value") else str(mem.role),
            )
            for mem, ws in res.all()
        ]
        active_workspace = workspaces[0] if workspaces else None
        return active_workspace, workspaces

    @staticmethod
    async def _ensure_default_workspace(db: AsyncSession, user: User) -> Workspace:
        """Ensure the user has at least one tenant workspace provisioned."""
        res = await db.execute(
            select(Membership, Workspace)
            .join(Workspace, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user.id)
        )
        existing = res.first()
        if existing:
            return existing[1]

        # Provision default workspace
        workspace_name = "Acme Corp"
        workspace_slug = f"acme-corp-{user.id.hex[:6]}"
        workspace = Workspace(
            name=workspace_name,
            slug=workspace_slug,
            settings={"created_via": "auto_provisioning"},
        )
        db.add(workspace)
        await db.flush()

        membership = Membership(
            workspace_id=workspace.id,
            user_id=user.id,
            role=Role.ADMIN,
        )
        db.add(membership)
        await db.flush()
        return workspace

    @staticmethod
    async def _issue_token_pair(
        db: AsyncSession, user: User, family_id: Optional[str] = None
    ) -> tuple[str, str, int]:
        """Issue an access token and a rotating refresh token, storing the refresh token hash."""
        access_token = create_access_token(user_id=user.id, email=user.email)
        raw_refresh, jti, token_family, expires_at = create_refresh_token(
            user_id=user.id, family_id=family_id
        )

        refresh_record = RefreshToken(
            user_id=user.id,
            token_jti=jti,
            token_hash=hash_token(raw_refresh),
            family_id=token_family,
            expires_at=expires_at,
        )
        db.add(refresh_record)
        await db.flush()

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, raw_refresh, expires_in

    @staticmethod
    async def register_user(
        db: AsyncSession, payload: UserRegisterRequest
    ) -> tuple[User, str, str, int, WorkspaceSummary | None, list[WorkspaceSummary]]:
        """Register a new user with Bcrypt password hashing and issue JWT token pair."""
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        await db.flush()

        await AuthService._ensure_default_workspace(db, user)
        access_token, refresh_token, expires_in = await AuthService._issue_token_pair(db, user)
        await db.commit()

        active_ws, all_ws = await AuthService.get_user_workspaces(db, user.id)
        return user, access_token, refresh_token, expires_in, active_ws, all_ws

    @staticmethod
    async def authenticate(
        db: AsyncSession, email: str, password: str
    ) -> tuple[User, str, str, int, WorkspaceSummary | None, list[WorkspaceSummary]]:
        """Verify Bcrypt password and issue fresh JWT token pair."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            masked_email = f"{email[:3]}***@{email.split('@')[-1]}" if "@" in email else "unknown"
            logger.warning(f"[auth] Failed login attempt for user={masked_email} (invalid_credentials)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        if not user.is_active:
            logger.warning(f"[auth] Login rejected for deactivated user={user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        await AuthService._ensure_default_workspace(db, user)
        access_token, refresh_token, expires_in = await AuthService._issue_token_pair(db, user)
        await db.commit()

        active_ws, all_ws = await AuthService.get_user_workspaces(db, user.id)
        return user, access_token, refresh_token, expires_in, active_ws, all_ws

    @staticmethod
    async def authenticate_google(
        db: AsyncSession, email: str, full_name: str, google_sub: str = ""
    ) -> tuple[User, str, str, int, WorkspaceSummary | None, list[WorkspaceSummary]]:
        """Authenticate or register a user via Google OAuth and issue JWT token pair."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                full_name=full_name or email.split("@")[0].capitalize(),
                password_hash=None,
            )
            db.add(user)
            await db.flush()

            identity = Identity(
                user_id=user.id,
                provider="google",
                provider_subject=google_sub or str(uuid.uuid4()),
                email=email,
            )
            db.add(identity)
            await db.flush()

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        await AuthService._ensure_default_workspace(db, user)
        access_token, refresh_token, expires_in = await AuthService._issue_token_pair(db, user)
        await db.commit()

        active_ws, all_ws = await AuthService.get_user_workspaces(db, user.id)
        return user, access_token, refresh_token, expires_in, active_ws, all_ws

    @staticmethod
    async def refresh_token_pair(
        db: AsyncSession, raw_refresh_token: str
    ) -> tuple[User, str, str, int, WorkspaceSummary | None, list[WorkspaceSummary]]:
        """Rotate refresh token: detect token reuse attacks, invalidate old token, issue fresh pair."""
        payload = decode_token(raw_refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        family_id = payload.get("family_id")
        user_id_str = payload.get("sub")

        if not jti or not family_id or not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed refresh token claims.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_hash_val = hash_token(raw_refresh_token)
        res = await db.execute(
            select(RefreshToken).where(
                (RefreshToken.token_jti == jti) | (RefreshToken.token_hash == token_hash_val)
            )
        )
        record = res.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not recognized or already purged.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # REUSE DETECTION: If token was already revoked or replaced, this is a replay / theft attack!
        if record.revoked_at is not None or record.replaced_by_jti is not None:
            logger.warning(
                f"[security] Refresh token reuse detected for family={record.family_id}. "
                f"Revoking all sessions in token family."
            )
            # Revoke entire token family immediately for security
            await db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == record.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Compromised token reuse detected. All sessions in this family have been revoked. Please re-authenticate.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        if record.expires_at.tzinfo is None:
            record_exp = record.expires_at.replace(tzinfo=timezone.utc)
        else:
            record_exp = record.expires_at

        if record_exp < now:
            logger.warning(f"[auth] Expired refresh token rejected for user={record.user_id}")
            record.revoked_at = now
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch user
        user = await db.get(User, record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Issue new pair in the same token family
        new_access_token = create_access_token(user_id=user.id, email=user.email)
        new_raw_refresh, new_jti, _, new_exp = create_refresh_token(
            user_id=user.id, family_id=record.family_id
        )

        new_record = RefreshToken(
            user_id=user.id,
            token_jti=new_jti,
            token_hash=hash_token(new_raw_refresh),
            family_id=record.family_id,
            expires_at=new_exp,
        )
        db.add(new_record)

        # Mark previous token as replaced & revoked
        record.replaced_by_jti = new_jti
        record.revoked_at = now
        await db.commit()

        active_ws, all_ws = await AuthService.get_user_workspaces(db, user.id)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return user, new_access_token, new_raw_refresh, expires_in, active_ws, all_ws

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> bool:
        """Revoke a refresh token and its family."""
        try:
            payload = decode_token(raw_refresh_token, expected_type="refresh")
            family_id = payload.get("family_id")
            jti = payload.get("jti")
        except Exception:
            family_id = None
            jti = None

        now = datetime.now(timezone.utc)
        token_hash_val = hash_token(raw_refresh_token)

        if family_id:
            await db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            await db.commit()
            return True

        # Fallback to single token lookup by jti or hash
        res = await db.execute(
            select(RefreshToken).where(
                (RefreshToken.token_hash == token_hash_val) | (RefreshToken.token_jti == jti)
            )
        )
        record = res.scalar_one_or_none()
        if record:
            record.revoked_at = now
            await db.commit()
            return True

        return False


IdentityService = AuthService


class WorkspaceService:
    """Operations for workspace provisioning and tenancy."""

    @staticmethod
    async def create_workspace(
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        payload: WorkspaceCreateRequest,
    ) -> Workspace:
        """Create a new tenant workspace and assign initial admin membership.

        ``user_id`` is optional because workspace provisioning may be invoked
        without an authenticated caller. A membership is only created when the
        referenced user actually exists, preventing a ForeignKeyViolationError
        from an unpersisted/random identifier.
        """
        existing = await db.execute(select(Workspace).where(Workspace.slug == payload.slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Workspace with slug '{payload.slug}' already exists.")

        workspace = Workspace(name=payload.name, slug=payload.slug)
        db.add(workspace)
        await db.flush()

        # Add creator as ADMIN only when the user exists in this database.
        if user_id is not None:
            user = await db.get(User, user_id)
            if user is not None:
                membership = Membership(workspace_id=workspace.id, user_id=user_id, role=Role.ADMIN)
                db.add(membership)

        await db.commit()
        await db.refresh(workspace)

        # Bust the workspace ID cache so the user gets the new workspace on next request
        if user_id is not None:
            await invalidate_workspace_cache(user_id)
        return workspace

    @staticmethod
    async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Optional[Workspace]:
        """Retrieve workspace by ID."""
        return await db.get(Workspace, workspace_id)

    @staticmethod
    async def get_user_membership(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Membership]:
        """Retrieve a user's membership in a workspace."""
        res = await db.execute(
            select(Membership).where(
                Membership.workspace_id == workspace_id,
                Membership.user_id == user_id,
            )
        )
        return res.scalar_one_or_none()

    @staticmethod
    async def list_members(db: AsyncSession, workspace_id: uuid.UUID) -> list[Membership]:
        """List all member accounts in a workspace."""
        res = await db.execute(select(Membership).where(Membership.workspace_id == workspace_id))
        return list(res.scalars().all())

    @staticmethod
    async def get_valid_invitation(
        db: AsyncSession,
        token_hash: str,
    ) -> Optional[Invitation]:
        """Look up an invitation strictly constraining to unexpired, unaccepted rows at DB query level.

        Fix #9 (Security Audit): Time-constrain invitation token queries in SQL
        using `expires_at > NOW()` and `accepted_at IS NULL` so expired
        or previously accepted tokens are filtered out directly by the DB query.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Invitation)
            .where(
                Invitation.token_hash == token_hash,
                Invitation.expires_at > now,
                Invitation.accepted_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        email: str,
        role: Role = Role.MEMBER,
        expires_delta_hours: int = 48,
    ) -> tuple[Invitation, str]:
        """Create a workspace invitation with a secure token."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_delta_hours)

        invitation = Invitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(invitation)
        await db.flush()
        return invitation, raw_token


async def invalidate_workspace_cache(user_id: uuid.UUID) -> None:
    """Bust the cached workspace ID for a user (call on workspace create/membership change)."""
    try:
        await delete_key(f"ws_id_cache:{user_id}")
    except Exception:
        pass  # Redis unavailable — no-op; cache will expire naturally


async def get_active_workspace_id(
    db: AsyncSession,
    user: Optional[User] = None,
    workspace_id: Optional[uuid.UUID] = None,
) -> uuid.UUID:
    """Resolve active tenant workspace ID with strict multi-tenant isolation.

    Guarantees:
    - 401 Unauthorized if user is None.
    - 403 Forbidden if user requests a workspace they do not belong to.
    - 403 Forbidden if user has no workspace memberships.
    - Zero phantom fallbacks (Workspace.limit(1) completely eliminated).
    """
    if user is None or not hasattr(user, "id") or not getattr(user, "id", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access workspace data",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. If explicit workspace requested (e.g. from X-Workspace-Id header), verify membership
    if workspace_id:
        mem_stmt = select(Membership).where(
            Membership.user_id == user.id,
            Membership.workspace_id == workspace_id,
        )
        mem_res = await db.execute(mem_stmt)
        mem = mem_res.scalar_one_or_none()
        if not mem:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: User is not a member of the requested workspace",
            )
        return workspace_id

    # 2. Check Redis cached active workspace for user
    cache_key = f"ws_id_cache:{user.id}"
    try:
        cached = await get_value(cache_key)
        if cached:
            return uuid.UUID(cached)
    except Exception:
        pass  # Redis unavailable — proceed to DB lookup

    # 3. Lookup user's workspace membership from database
    mem_res = await db.execute(
        select(Membership).where(Membership.user_id == user.id).limit(1)
    )
    mem = mem_res.scalar_one_or_none()
    if mem:
        try:
            await set_with_ttl(cache_key, str(mem.workspace_id), ttl_seconds=300)
        except Exception:
            pass
        return mem.workspace_id

    # 4. If user has no active memberships, fail fast with 403 Forbidden
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No active workspace membership found for this user",
    )


_get_active_workspace_id = get_active_workspace_id


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Retrieve user entity by primary key."""
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


IdentityService.get_user_by_id = staticmethod(get_user_by_id)


