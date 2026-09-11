"""Workspaces service for provisioning and membership management."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import Role
from modules.workspaces.models import Membership, Workspace
from modules.workspaces.schemas import WorkspaceCreateRequest


class WorkspaceService:
    """Workspace operations and membership RBAC enforcement."""

    @staticmethod
    async def create_workspace(
        db: AsyncSession,
        creator_user_id: uuid.UUID,
        payload: WorkspaceCreateRequest,
    ) -> Workspace:
        """Create a workspace and assign the creator as the initial Admin."""
        existing = await db.execute(select(Workspace).where(Workspace.slug == payload.slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Workspace with slug '{payload.slug}' already exists.")

        workspace = Workspace(name=payload.name, slug=payload.slug)
        db.add(workspace)
        await db.flush()

        membership = Membership(
            workspace_id=workspace.id,
            user_id=creator_user_id,
            role=Role.ADMIN,
        )
        db.add(membership)
        await db.commit()
        return workspace

    @staticmethod
    async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
        """Retrieve workspace by ID."""
        result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_members(db: AsyncSession, workspace_id: uuid.UUID) -> list[Membership]:
        """List all members within a workspace."""
        result = await db.execute(select(Membership).where(Membership.workspace_id == workspace_id))
        return list(result.scalars().all())
