"""Workspace management and resolution service."""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import Role
from modules.identity.models import User
from modules.workspaces.models import Membership, Workspace
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


async def get_active_workspace_id(db: AsyncSession, user: Optional[User] = None) -> uuid.UUID:
    """Get active workspace ID or fallback to first existing workspace."""
    if user:
        mem_res = await db.execute(select(Membership).where(Membership.user_id == user.id))
        mem = mem_res.scalar_one_or_none()
        if mem:
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
