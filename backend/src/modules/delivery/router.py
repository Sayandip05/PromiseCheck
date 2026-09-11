"""Delivery and fulfillment verification router."""

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/delivery", tags=["Delivery Verification"])


class DeliveryEvidenceResponse(BaseModel):
    """Evidence proving a customer commitment was fulfilled."""

    id: uuid.UUID
    commitment_id: uuid.UUID
    evidence_type: str  # release_note, pull_request, manual_signoff
    verified_by_user_id: uuid.UUID
    verified_at: datetime


@router.get("/evidence", response_model=list[DeliveryEvidenceResponse])
async def list_delivery_evidence():
    """List verified delivery records."""
    return []
