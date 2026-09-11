"""Risk evaluation module router."""

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/risk", tags=["Risk & Deadlines"])


class RiskAssessmentResponse(BaseModel):
    """Calculated delivery risk assessment for a commitment."""

    commitment_id: uuid.UUID
    risk_level: str  # low, medium, high, overdue
    conflict_days: int = 0
    reason: str


@router.get("/assessments", response_model=list[RiskAssessmentResponse])
async def list_risk_assessments():
    """List current commitment risk evaluations."""
    return []
