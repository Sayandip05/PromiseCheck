"""Risk evaluation REST router."""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.commitments.risk.schemas import RiskAssessmentResponse, RiskEvaluationSummary
from modules.commitments.risk.service import RiskService
from modules.iam import User, get_active_workspace_id, get_current_user

router = APIRouter(prefix="/risk", tags=["Risk & Deadlines"])


@router.get("/assessments", response_model=list[RiskAssessmentResponse])
async def list_risk_assessments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List current commitment risk evaluations."""
    ws_id = await get_active_workspace_id(db, user)
    assessments = await RiskService.list_risk_assessments(db, ws_id)
    return [RiskAssessmentResponse(**a) for a in assessments]


@router.post("/evaluate", response_model=RiskEvaluationSummary)
async def evaluate_workspace_risk(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Scan all active commitments, calculate timeline risks, and update statuses."""
    ws_id = await get_active_workspace_id(db, user)
    summary = await RiskService.evaluate_workspace_risk(db, ws_id, user.id if user else None)
    return RiskEvaluationSummary(**summary)
