"""Delivery and fulfillment verification router."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import publish_event
from core.security import get_current_user, get_current_user_optional
from modules.audit.service import record_audit_event
from modules.commitments.models import Commitment
from modules.delivery.models import DeliveryEvidence
from modules.identity.models import User
from modules.workspaces.service import get_active_workspace_id

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
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List verified delivery records for the active workspace."""
    ws_id = await get_active_workspace_id(db, user)

    # 1. Query real DeliveryEvidence rows
    res = await db.execute(
        select(DeliveryEvidence)
        .where(DeliveryEvidence.workspace_id == ws_id)
        .order_by(desc(DeliveryEvidence.created_at))
    )
    ev_records = res.scalars().all()

    if ev_records:
        return [
            DeliveryEvidenceResponse(
                id=str(r.id),
                commitment_id=str(r.commitment_id),
                commitment_title=r.commitment_title,
                customer_name=r.customer_name,
                evidence_type=r.evidence_type,
                evidence_title=r.evidence_title,
                evidence_url=r.evidence_url,
                verified_by=r.verified_by,
                verified_at=r.created_at.strftime("%b %d, %Y"),
            )
            for r in ev_records
        ]

    # 2. Fallback to extracting from commitments table if no explicit sign-off rows yet
    commitments_res = await db.execute(select(Commitment).where(Commitment.workspace_id == ws_id))
    commitments = commitments_res.scalars().all()

    records: list[DeliveryEvidenceResponse] = []
    for c in commitments:
        ev = c.engineering_evidence_json or {}
        for rel in ev.get("releaseNotes", []):
            records.append(
                DeliveryEvidenceResponse(
                    id=f"ev-rel-{str(c.id)[:8]}",
                    commitment_id=str(c.id),
                    commitment_title=c.title,
                    customer_name=c.customer_name,
                    evidence_type="release_notes",
                    evidence_title=rel,
                    verified_at=datetime.now(timezone.utc).strftime("%b %d, %Y"),
                )
            )
        for pr in ev.get("prs", []):
            records.append(
                DeliveryEvidenceResponse(
                    id=f"ev-pr-{str(c.id)[:8]}",
                    commitment_id=str(c.id),
                    commitment_title=c.title,
                    customer_name=c.customer_name,
                    evidence_type="pr_merged",
                    evidence_title=pr.get("title", f"PR #{pr.get('number', '')}"),
                    verified_at=datetime.now(timezone.utc).strftime("%b %d, %Y"),
                )
            )

    return records


@router.post("/verify", response_model=DeliveryEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def verify_commitment_delivery(
    payload: VerifyDeliveryRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Officially mark a commitment delivered and store verified evidence proof."""
    ws_id = await get_active_workspace_id(db, user)
    c = await db.get(Commitment, payload.commitment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    # 1. Update commitment status to delivered
    c.status = "delivered"
    c.status_label = "Delivered"
    c.category = "delivered"
    c.is_confirmed = True

    # Update evidence JSON payload
    ev_json = dict(c.engineering_evidence_json or {})
    if payload.evidence_type == "release_notes":
        rels = list(ev_json.get("releaseNotes", []))
        rels.append(payload.evidence_title)
        ev_json["releaseNotes"] = rels
    elif payload.evidence_type == "pr_merged":
        prs = list(ev_json.get("prs", []))
        prs.append({"title": payload.evidence_title, "url": payload.evidence_url})
        ev_json["prs"] = prs
    c.engineering_evidence_json = ev_json

    # 2. Persist DeliveryEvidence record
    verifier_name = user.full_name if user else "Lead Engineer"
    evidence_row = DeliveryEvidence(
        workspace_id=ws_id,
        commitment_id=c.id,
        commitment_title=c.title,
        customer_name=c.customer_name,
        evidence_type=payload.evidence_type,
        evidence_title=payload.evidence_title,
        evidence_url=payload.evidence_url or "",
        verified_by=verifier_name,
        notes=payload.notes or "",
    )
    db.add(evidence_row)

    # 3. Record compliance audit trail
    await record_audit_event(
        db=db,
        workspace_id=ws_id,
        actor_id=user.id if user else ws_id,
        action="COMMITMENT_DELIVERED",
        target_type="commitment",
        target_id=str(c.id),
        description=f"Verified delivery of '{c.title}' for {c.customer_name} via {payload.evidence_type} ({payload.evidence_title}).",
        payload={
            "evidence_type": payload.evidence_type,
            "evidence_title": payload.evidence_title,
            "verified_by": verifier_name,
        },
    )

    await db.commit()
    await db.refresh(evidence_row)

    # 4. Broadcast event across Redis Pub/Sub
    await publish_event(
        f"ws:{ws_id}:events",
        "COMMITMENT_DELIVERED",
        {
            "commitment_id": str(c.id),
            "title": c.title,
            "customer": c.customer_name,
            "evidence_title": payload.evidence_title,
        },
    )

    return DeliveryEvidenceResponse(
        id=str(evidence_row.id),
        commitment_id=str(c.id),
        commitment_title=c.title,
        customer_name=c.customer_name,
        evidence_type=evidence_row.evidence_type,
        evidence_title=evidence_row.evidence_title,
        evidence_url=evidence_row.evidence_url,
        verified_by=evidence_row.verified_by,
        verified_at=evidence_row.created_at.strftime("%b %d, %Y"),
    )
