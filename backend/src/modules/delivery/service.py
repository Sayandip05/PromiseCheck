"""Delivery domain service for commitment fulfillment verification and evidence proof."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import publish_event
from modules.audit.service import record_audit_event
from modules.commitments.service import CommitmentService
from modules.delivery.models import DeliveryEvidence
from modules.iam.models import User


class DeliveryService:
    """Encapsulates delivery verification, sign-off evidence persistence, and audit logging."""

    @staticmethod
    async def list_evidence(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Retrieve delivery evidence records with fallback to engineering evidence."""
        # 1. Primary: query explicit sign-off rows
        evidence_stmt = (
            select(DeliveryEvidence)
            .where(DeliveryEvidence.workspace_id == workspace_id)
            .order_by(desc(DeliveryEvidence.created_at))
        )
        res = await db.execute(evidence_stmt)
        ev_records = res.scalars().all()

        if ev_records:
            return [
                {
                    "id": str(r.id),
                    "commitment_id": str(r.commitment_id),
                    "commitment_title": r.commitment_title,
                    "customer_name": r.customer_name,
                    "evidence_type": r.evidence_type,
                    "evidence_title": r.evidence_title,
                    "evidence_url": r.evidence_url or "",
                    "verified_at": r.created_at.strftime("%b %d, %Y"),
                    "verified_by": r.verified_by or "Lead Engineer",
                }
                for r in ev_records
            ]

        # 2. Fallback: extract from commitments via CommitmentService
        commitments = await CommitmentService.list_all_workspace_commitments(db, workspace_id)
        records: list[dict[str, Any]] = []
        for c in commitments:
            ev = c.engineering_evidence_json or {}
            for rel in ev.get("releaseNotes", []):
                records.append({
                    "id": f"ev-rel-{str(c.id)[:8]}",
                    "commitment_id": str(c.id),
                    "commitment_title": c.title,
                    "customer_name": c.customer_name,
                    "evidence_type": "release_notes",
                    "evidence_title": rel,
                    "evidence_url": "",
                    "verified_at": datetime.now(timezone.utc).strftime("%b %d, %Y"),
                    "verified_by": "Lead Engineer",
                })
            for pr in ev.get("prs", []):
                records.append({
                    "id": f"ev-pr-{str(c.id)[:8]}",
                    "commitment_id": str(c.id),
                    "commitment_title": c.title,
                    "customer_name": c.customer_name,
                    "evidence_type": "pr_merged",
                    "evidence_title": pr.get("title", f"PR #{pr.get('number', '')}"),
                    "evidence_url": pr.get("url", ""),
                    "verified_at": datetime.now(timezone.utc).strftime("%b %d, %Y"),
                    "verified_by": "Lead Engineer",
                })
        return records

    @staticmethod
    async def verify_delivery(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user: Optional[User],
        commitment_id: uuid.UUID,
        evidence_type: str,
        evidence_title: str,
        evidence_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Mark commitment delivered and persist signed evidence proof."""
        c = await CommitmentService.mark_delivered(
            db=db,
            commitment_id=commitment_id,
            workspace_id=workspace_id,
            evidence_type=evidence_type,
            evidence_title=evidence_title,
            evidence_url=evidence_url,
        )
        if not c:
            raise HTTPException(status_code=404, detail="Commitment not found")

        verifier_name = user.full_name if user else "Lead Engineer"
        evidence_row = DeliveryEvidence(
            workspace_id=workspace_id,
            commitment_id=commitment_id,
            commitment_title=c.title,
            customer_name=c.customer_name,
            evidence_type=evidence_type,
            evidence_title=evidence_title,
            evidence_url=evidence_url or "",
            verified_by=verifier_name,
            notes=notes or "",
        )
        db.add(evidence_row)

        await record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor_id=user.id if user else workspace_id,
            action="COMMITMENT_DELIVERED",
            target_type="commitment",
            target_id=str(c.id),
            description=f"Verified delivery of '{c.title}' with proof: {evidence_title}.",
            payload={
                "evidence_type": evidence_type,
                "evidence_title": evidence_title,
                "evidence_url": evidence_url,
            },
        )
        await db.commit()
        await db.refresh(evidence_row)

        await publish_event(
            f"ws:{workspace_id}:events",
            "COMMITMENT_DELIVERED",
            {
                "commitment_id": str(c.id),
                "customer": c.customer_name,
                "evidence_title": evidence_title,
                "evidence_type": evidence_type,
            },
        )

        return {
            "id": str(evidence_row.id),
            "commitment_id": str(c.id),
            "commitment_title": c.title,
            "customer_name": c.customer_name,
            "evidence_type": evidence_type,
            "evidence_title": evidence_title,
            "evidence_url": evidence_url or "",
            "verified_at": evidence_row.created_at.strftime("%b %d, %Y"),
            "verified_by": verifier_name,
        }
