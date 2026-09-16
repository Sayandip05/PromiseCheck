"""Risk evaluation module router."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import publish_event
from core.security import get_current_user_optional
from modules.audit.service import record_audit_event
from modules.commitments.models import Commitment
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/risk", tags=["Risk & Deadlines"])


class RiskAssessmentResponse(BaseModel):
    """Calculated delivery risk assessment for a commitment."""

    commitment_id: uuid.UUID
    commitment_title: str
    customer_name: str
    risk_level: str  # low, medium, high, overdue
    conflict_days: int = 0
    reason: str


class RiskEvaluationSummary(BaseModel):
    """Result summary of a workspace risk evaluation run."""

    evaluated_count: int
    at_risk_count: int
    overdue_count: int
    on_track_count: int
    timestamp: str


@router.get("/assessments", response_model=list[RiskAssessmentResponse])
async def list_risk_assessments(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List current commitment risk evaluations."""
    ws_id = await get_active_workspace_id(db, user)
    stmt = select(Commitment).where(Commitment.workspace_id == ws_id)
    result = await db.execute(stmt)
    commitments = result.scalars().all()

    assessments: list[RiskAssessmentResponse] = []
    for c in commitments:
        risk = c.risk_json or {}
        level = risk.get("level") or (
            "high" if c.status == "at-risk" else "overdue" if c.status == "overdue" else "low"
        )
        reason = risk.get("reason") or (
            f"Status is {c.status} with delivery due by {c.promised_by or 'upcoming sprint'}"
        )
        conflict_days = risk.get("conflictDays", 0)
        assessments.append(
            RiskAssessmentResponse(
                commitment_id=c.id,
                commitment_title=c.title,
                customer_name=c.customer_name,
                risk_level=level,
                conflict_days=conflict_days,
                reason=reason,
            )
        )
    return assessments


@router.post("/evaluate", response_model=RiskEvaluationSummary)
async def evaluate_workspace_risk(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Scan all active commitments, calculate timeline risks, update statuses, and log audit events."""
    ws_id = await get_active_workspace_id(db, user)
    stmt = select(Commitment).where(Commitment.workspace_id == ws_id)
    result = await db.execute(stmt)
    commitments = result.scalars().all()

    at_risk_count = 0
    overdue_count = 0
    on_track_count = 0
    now = datetime.now(timezone.utc)

    for c in commitments:
        # Don't alter already fulfilled commitments
        if c.status == "delivered":
            on_track_count += 1
            continue

        # Evaluate target date
        target_dt = None
        if c.promised_date_iso:
            try:
                target_dt = datetime.fromisoformat(c.promised_date_iso.replace("Z", "+00:00"))
                if target_dt.tzinfo is None:
                    target_dt = target_dt.replace(tzinfo=timezone.utc)
            except Exception:
                target_dt = None


        risk = c.risk_json or {}
        days_diff = None
        if target_dt:
            days_diff = (target_dt - now).days

        # Risk heuristics
        if days_diff is not None and days_diff < 0:
            c.status = "overdue"
            c.status_label = "Overdue"
            c.category = "at-risk"
            c.risk_json = {
                "level": "overdue",
                "reason": f"Delivery target passed {abs(days_diff)} day(s) ago without verified proof.",
                "conflictDays": abs(days_diff),
            }
            overdue_count += 1
        elif (days_diff is not None and days_diff <= 3) or c.status == "at-risk":
            c.status = "at-risk"
            c.status_label = "At Risk"
            c.category = "at-risk"
            c.risk_json = {
                "level": "high",
                "reason": risk.get("reason", "Milestone within 3 days without completed PR verification."),
                "conflictDays": risk.get("conflictDays", 3),
            }
            at_risk_count += 1
        else:
            on_track_count += 1
            if c.status not in ("delivered", "at-risk", "overdue"):
                c.status = "on-track"
                c.status_label = "On Track"

    await db.commit()

    # Immutable audit logging
    actor_id = user.id if user else uuid.uuid4()
    await record_audit_event(
        db=db,
        workspace_id=ws_id,
        actor_id=actor_id,
        action="risk_evaluated",
        target_type="risk_engine",
        target_id="workspace-scan",
        description=f"Automated risk evaluation completed: {at_risk_count} at-risk, {overdue_count} overdue, {on_track_count} on-track",
        payload={
            "at_risk_count": at_risk_count,
            "overdue_count": overdue_count,
            "on_track_count": on_track_count,
        },
    )
    await db.commit()

    # Broadcast event via Redis Pub/Sub
    await publish_event(
        f"ws:{ws_id}:events",
        "RISK_EVALUATION_COMPLETED",
        {
            "workspace_id": str(ws_id),
            "evaluated_count": len(commitments),
            "at_risk_count": at_risk_count,
            "overdue_count": overdue_count,
        },
    )


    return RiskEvaluationSummary(
        evaluated_count=len(commitments),
        at_risk_count=at_risk_count,
        overdue_count=overdue_count,
        on_track_count=on_track_count,
        timestamp=now.isoformat(),
    )
