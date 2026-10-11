"""Risk domain service for timeline heuristics, delivery probability, and SLA monitoring."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import publish_event
from modules.audit import record_audit_event
from modules.commitments.service import CommitmentService


class RiskService:
    """Encapsulates commitment deadline risk calculations, status updates, and audit tracking."""

    @staticmethod
    async def list_risk_assessments(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """List current commitment risk evaluations."""
        commitments = await CommitmentService.list_all_workspace_commitments(db, workspace_id)
        assessments: list[dict[str, Any]] = []
        for c in commitments:
            risk = c.risk_json or {}
            level = risk.get("level") or (
                "high" if c.status == "at-risk" else "overdue" if c.status == "overdue" else "low"
            )
            reason = risk.get("reason") or (
                f"Status is {c.status} with delivery due by {c.promised_by or 'upcoming sprint'}"
            )
            conflict_days = risk.get("conflictDays", 0)
            assessments.append({
                "commitment_id": c.id,
                "commitment_title": c.title,
                "customer_name": c.customer_name,
                "risk_level": level,
                "conflict_days": conflict_days,
                "reason": reason,
            })
        return assessments

    @staticmethod
    async def evaluate_workspace_risk(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """Scan all active commitments, calculate timeline risks, and update statuses."""
        commitments = await CommitmentService.list_all_workspace_commitments(db, workspace_id)

        at_risk_count = 0
        overdue_count = 0
        on_track_count = 0
        now = datetime.now(timezone.utc)

        for c in commitments:
            if c.status == "delivered":
                on_track_count += 1
                continue

            target_dt = None
            if c.due_date:
                target_dt = c.due_date if c.due_date.tzinfo else c.due_date.replace(tzinfo=timezone.utc)
            elif c.promised_date:
                target_dt = datetime(
                    c.promised_date.year,
                    c.promised_date.month,
                    c.promised_date.day,
                    tzinfo=timezone.utc,
                )

            risk = c.risk_json or {}
            days_diff = (target_dt - now).days if target_dt else None

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
                if c.status not in ("delivered", "at-risk", "overdue", "confirmed", "blocked", "awaiting-review"):
                    c.status = "confirmed"
                    c.status_label = "On Track"

        await db.commit()

        await record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor_id=user_id if user_id else workspace_id,
            action="RISK_EVALUATED",
            target_type="workspace",
            target_id=str(workspace_id),
            description=(
                f"Evaluated {len(commitments)} commitments: "
                f"{at_risk_count} at-risk, {overdue_count} overdue."
            ),
            payload={
                "at_risk_count": at_risk_count,
                "overdue_count": overdue_count,
                "on_track_count": on_track_count,
            },
        )

        summary = {
            "evaluated_count": len(commitments),
            "at_risk_count": at_risk_count,
            "overdue_count": overdue_count,
            "on_track_count": on_track_count,
            "timestamp": now.isoformat(),
        }

        await publish_event(
            f"ws:{workspace_id}:events",
            "RISK_EVALUATION_COMPLETED",
            summary,
        )

        return summary
