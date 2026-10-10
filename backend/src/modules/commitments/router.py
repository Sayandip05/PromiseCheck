"""Commitments REST router — thin HTTP controller delegating to CommitmentService."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from modules.commitments.schemas import (
    CommitmentCreateRequest,
    CommitmentDTO,
    CommitmentUpdateRequest,
    DraftUpdateRequest,
    DraftUpdateResponse,
    PaginatedCommitmentsResponse,
)
from modules.commitments.service import CommitmentService, to_dto
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/commitments", tags=["Commitments"])


@router.get("", response_model=PaginatedCommitmentsResponse)
async def list_commitments(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=100,
        ge=1,
        le=100,
        description="Items per page. Maximum 100.",
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve commitments for the user's workspace with evidence and risk metrics."""
    ws_id = await get_active_workspace_id(db, user)
    items, total = await CommitmentService.list_commitments(
        db=db,
        workspace_id=ws_id,
        status_filter=status_filter,
        category_filter=category_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedCommitmentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.post("", response_model=CommitmentDTO, status_code=status.HTTP_201_CREATED)
async def create_commitment(
    payload: CommitmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new tracked commitment."""
    ws_id = await get_active_workspace_id(db, user)
    commitment = await CommitmentService.create_commitment(
        db=db,
        workspace_id=ws_id,
        user=user,
        payload=payload,
    )
    return to_dto(commitment)


@router.get("/{commitment_id}", response_model=CommitmentDTO)
async def get_commitment(
    commitment_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve an individual commitment by UUID with workspace tenancy authorization."""
    ws_id = await get_active_workspace_id(db, user)
    c = await CommitmentService.get_by_id(db, commitment_id, ws_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    response.headers["ETag"] = f'W/"{c.id}:{int(c.updated_at.timestamp())}"'
    return to_dto(c)


@router.patch("/{commitment_id}", response_model=CommitmentDTO)
async def update_commitment(
    commitment_id: uuid.UUID,
    payload: CommitmentUpdateRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update title, status, or date of a commitment with optimistic concurrency control."""
    ws_id = await get_active_workspace_id(db, user)
    if_match = request.headers.get("if-match")
    c = await CommitmentService.update_commitment(
        db=db,
        commitment_id=commitment_id,
        workspace_id=ws_id,
        user=user,
        payload=payload,
        if_match=if_match,
    )
    response.headers["ETag"] = f'W/"{c.id}:{int(c.updated_at.timestamp())}"'
    return to_dto(c)


@router.post("/{commitment_id}/confirm", response_model=CommitmentDTO)
async def confirm_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Confirm a candidate commitment from the review queue into active tracking."""
    ws_id = await get_active_workspace_id(db, user)
    c = await CommitmentService.confirm_commitment(
        db=db,
        commitment_id=commitment_id,
        workspace_id=ws_id,
        user=user,
    )
    return to_dto(c)


@router.post("/{commitment_id}/draft-update", response_model=DraftUpdateResponse)
async def generate_draft_update(
    commitment_id: uuid.UUID,
    payload: Optional[DraftUpdateRequest] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate an AI-crafted transparent customer status email / message update."""
    ws_id = await get_active_workspace_id(db, user)
    recipient = payload.recipient_name if payload else None
    return await CommitmentService.generate_draft_update(
        db=db,
        commitment_id=commitment_id,
        workspace_id=ws_id,
        recipient_name=recipient,
    )


@router.delete("/{commitment_id}", status_code=status.HTTP_200_OK)
async def delete_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a commitment within tenant boundary."""
    ws_id = await get_active_workspace_id(db, user)
    deleted_id, _ = await CommitmentService.delete_commitment(
        db=db,
        commitment_id=commitment_id,
        workspace_id=ws_id,
        user=user,
    )
    return {"status": "deleted", "id": deleted_id}
