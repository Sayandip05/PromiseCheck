"""Delivery and fulfillment verification REST router."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.iam.dependencies import get_current_user
from modules.commitments.delivery.service import DeliveryService
from modules.iam.models import User
from modules.iam.service import get_active_workspace_id

router = APIRouter(prefix="/delivery", tags=["Delivery Verification"])


class DeliveryEvidenceResponse(BaseModel):
    """Evidence proving a customer commitment was fulfilled."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    commitment_id: str
    commitment_title: str
    customer_name: str
    evidence_type: str  # release_notes, pr_merged, manual_signoff
    evidence_title: str
    verified_at: str
    verified_by: Optional[str] = "Team Lead"
    evidence_url: Optional[str] = ""


class VerifyDeliveryRequest(BaseModel):
    """Request payload to officially mark a commitment fulfilled with proof."""

    commitment_id: uuid.UUID
    evidence_type: str = "manual_signoff"  # release_notes | pr_merged | manual_signoff
    evidence_title: str
    evidence_url: Optional[str] = ""
    notes: Optional[str] = ""


@router.get("/evidence", response_model=list[DeliveryEvidenceResponse])
async def list_delivery_evidence(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List verified delivery sign-offs and evidence proofs for the active workspace."""
    ws_id = await get_active_workspace_id(db, user)
    records = await DeliveryService.list_evidence(db, ws_id)
    return [DeliveryEvidenceResponse(**r) for r in records]


@router.post("/verify", response_model=DeliveryEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def verify_commitment_delivery(
    payload: VerifyDeliveryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Officially mark a commitment delivered and store verified evidence proof."""
    ws_id = await get_active_workspace_id(db, user)
    res = await DeliveryService.verify_delivery(
        db=db,
        workspace_id=ws_id,
        user=user,
        commitment_id=payload.commitment_id,
        evidence_type=payload.evidence_type,
        evidence_title=payload.evidence_title,
        evidence_url=payload.evidence_url,
        notes=payload.notes,
    )
    return DeliveryEvidenceResponse(**res)
