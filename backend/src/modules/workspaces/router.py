"""Workspaces management and membership routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.workspaces.schemas import MembershipResponse, WorkspaceCreateRequest, WorkspaceResponse
from modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces & Tenancy"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new tenant workspace."""
    try:
        # For Phase 1 scaffold, provision root workspace
        system_user_id = uuid.uuid4()
        workspace = await WorkspaceService.create_workspace(db, system_user_id, payload)
        return workspace
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve workspace details."""
    workspace = await WorkspaceService.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return workspace


@router.get("/{workspace_id}/members", response_model=list[MembershipResponse])
async def list_workspace_members(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List members and their roles within a workspace."""
    return await WorkspaceService.list_members(db, workspace_id)
