"""Commitments router."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.commitments.models import Commitment
from modules.commitments.schemas import CommitmentCreateRequest, CommitmentResponse

router = APIRouter(prefix="/commitments", tags=["Commitments"])


@router.get("", response_model=list[CommitmentResponse])
async def list_commitments(db: AsyncSession = Depends(get_db)):
    """List customer commitments (placeholder implementation)."""
    result = await db.execute(select(Commitment).limit(50))
    return list(result.scalars().all())


@router.post("", response_model=CommitmentResponse)
async def create_commitment(payload: CommitmentCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new commitment."""
    # Placeholder implementation
    commitment = Commitment(
        workspace_id=uuid.uuid4(),
        title=payload.title,
        quote=payload.quote,
        customer_id=payload.customer_id,
        owner_id=payload.owner_id,
        due_date=payload.due_date,
    )
    db.add(commitment)
    await db.commit()
    return commitment
