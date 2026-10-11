"""Delivery and fulfillment verification REST router."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.commitments.delivery.schemas import DeliveryEvidenceResponse, VerifyDeliveryRequest
from modules.commitments.delivery.service import DeliveryService
from modules.iam import User, get_active_workspace_id, get_current_user

router = APIRouter(prefix="/delivery", tags=["Delivery Verification"])


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
