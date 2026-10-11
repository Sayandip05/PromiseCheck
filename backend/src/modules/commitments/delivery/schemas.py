"""Delivery sub-module Pydantic schemas."""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
