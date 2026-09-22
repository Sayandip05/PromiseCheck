"""Workspace management and resolution service."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import Role
from core.redis import delete_key, get_value, set_with_ttl
from modules.identity.models import User
from modules.workspaces.models import Invitation, Membership, Workspace
from modules.workspaces.schemas import WorkspaceCreateRequest


class WorkspaceService:
    """Operations for workspace provisioning and tenancy."""

    @staticmethod
    async def create_workspace(
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: WorkspaceCreateRequest,
    ) -> Workspace:
        """Create a new tenant workspace and assign initial admin membership."""
        existing = await db.execute(select(Workspace).where(Workspace.slug == payload.slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Workspace with slug '{payload.slug}' already exists.")

        workspace = Workspace(name=payload.name, slug=payload.slug)
        db.add(workspace)
        await db.flush()

        # Add creator as ADMIN if user exists
        membership = Membership(workspace_id=workspace.id, user_id=user_id, role=Role.ADMIN)
        db.add(membership)
        await db.commit()
        await db.refresh(workspace)

        # Bust the workspace ID cache so the user gets the new workspace on next request
        await invalidate_workspace_cache(user_id)
        return workspace

    @staticmethod
    async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Optional[Workspace]:
        """Retrieve workspace by ID."""
        return await db.get(Workspace, workspace_id)

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


async def get_active_workspace_id(db: AsyncSession, user: Optional[User] = None) -> uuid.UUID:
    """Get active workspace ID or fallback to first existing workspace.

    Fix #7: Checks a Redis cache key (ws_id_cache:{user_id}, 5-min TTL) before
    executing the membership DB query. At 1,000 RPS this previously caused 1,000
    unnecessary DB reads/sec. Cache miss occurs only on first request after login
    or workspace membership change.
    """
    if user:
        cache_key = f"ws_id_cache:{user.id}"
        try:
            cached = await get_value(cache_key)
            if cached:
                return uuid.UUID(cached)
        except Exception:
            pass  # Redis unavailable — proceed to DB lookup

        mem_res = await db.execute(select(Membership).where(Membership.user_id == user.id))
        mem = mem_res.scalar_one_or_none()
        if mem:
            try:
                await set_with_ttl(cache_key, str(mem.workspace_id), ttl_seconds=300)
            except Exception:
                pass  # Redis unavailable — no-op, just don't cache
            return mem.workspace_id

    ws_res = await db.execute(select(Workspace).limit(1))
    ws = ws_res.scalar_one_or_none()
    if ws:
        return ws.id

    # Create fallback default workspace
    fallback_ws = Workspace(name="Acme Corp", slug="acme-corp-main")
    db.add(fallback_ws)
    await db.flush()
    return fallback_ws.id


_get_active_workspace_id = get_active_workspace_id
