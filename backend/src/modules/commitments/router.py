"""Commitments REST router with full lifecycle, evidence tracking, and AI drafting."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_async_redis
from core.security import get_current_user, get_current_user_optional
from modules.commitments.models import Commitment
from modules.commitments.schemas import (
    CommitmentCreateRequest,
    CommitmentDTO,
    CommitmentUpdateRequest,
    DraftUpdateRequest,
    DraftUpdateResponse,
    EngineeringEvidenceSchema,
    OriginalPromiseSchema,
    OwnerSchema,
    PaginatedCommitmentsResponse,
    RecommendedStepSchema,
    RiskAnalysisSchema,
)
from modules.identity.models import User
from modules.workspaces.models import Membership, Workspace
from modules.workspaces.service import get_active_workspace_id
from core.redis import publish_event
from modules.audit.service import record_audit_event

router = APIRouter(prefix="/commitments", tags=["Commitments"])


def _to_dto(c: Commitment) -> CommitmentDTO:
    """Convert Commitment DB entity to frontend DTO."""
    owner_initials = "".join([part[0] for part in c.owner_name.split() if part])[:2].upper() or "MC"
    orig = c.original_promise_json or {}
    eng = c.engineering_evidence_json or {}
    risk = c.risk_json or {}
    step = c.recommended_step_json or {}

    return CommitmentDTO(
        id=str(c.id),
        title=c.title,
        customer=c.customer_name,
        owner=OwnerSchema(
            name=c.owner_name,
            initials=owner_initials,
            avatarColor="bg-neutral-200 text-neutral-800",
            email=c.owner_email,
        ),
        promisedBy=c.promised_by or "TBD",
        promisedDateIso=c.promised_date_iso or "",
        status=c.status,
        statusLabel=c.status_label,
        isConfirmed=c.is_confirmed,
        category=c.category,
        originalPromise=OriginalPromiseSchema(
            quote=orig.get("quote", c.quote or c.title),
            sourceTitle=orig.get("sourceTitle", "Customer Onboarding Call"),
            timestamp=orig.get("timestamp", "Recent"),
            transcriptId=orig.get("transcriptId"),
        ),
        engineeringEvidence=(
            EngineeringEvidenceSchema(**eng) if eng and eng.get("ticketId") else None
        ),
        risk=RiskAnalysisSchema(**risk) if risk else None,
        recommendedNextStep=RecommendedStepSchema(**step) if step else None,
    )


_get_active_workspace_id = get_active_workspace_id


async def _seed_default_commitments_if_empty(db: AsyncSession, workspace_id: uuid.UUID):
    """Seed initial high-fidelity commitments if table is empty for instant UX vibrancy.

    Fix #8: Guards with a Redis distributed lock (nx=True, ex=10) and a permanent
    'seeded' marker so:
    - Concurrent first-requests don't race to insert duplicate seeds.
    - Subsequent requests skip the DB check entirely (fast Redis EXISTS, no query).
    """
    try:
        r = get_async_redis()
        seeded_key = f"seeded:{workspace_id}"
        lock_key = f"seed_lock:{workspace_id}"

        # Fast exit: workspace was already seeded — no DB round-trip needed
        if await r.exists(seeded_key):
            return

        # Acquire distributed lock: SET NX EX 10
        # Only one worker proceeds; others see the lock and bail out.
        acquired = await r.set(lock_key, "1", nx=True, ex=10)
        if not acquired:
            return  # Another worker holds the lock and is seeding right now
    except Exception:
        # Redis unavailable: fall through to the DB check (safe, just not optimised)
        r = None
        acquired = True
        seeded_key = lock_key = None

    try:
        res = await db.execute(select(Commitment).where(Commitment.workspace_id == workspace_id).limit(1))
        if res.scalar_one_or_none():
            if r and seeded_key:
                await r.set(seeded_key, "1")  # Back-fill marker for future requests
            return

        seeds = [
        Commitment(
            workspace_id=workspace_id,
            title="Enable SSO",
            customer_name="Acme",
            owner_name="Maya Chen",
            owner_email="maya@acme.corp",
            promised_by="Sep 30, 2026",
            promised_date_iso="2026-09-30",
            status="at-risk",
            status_label="At risk",
            is_confirmed=True,
            category="needs-attention",
            quote="We'll enable SSO for your team by September 30.",
            original_promise_json={
                "quote": "We'll enable SSO for your team by September 30.",
                "sourceTitle": "Acme onboarding",
                "timestamp": "Sep 18 · 14:32",
                "transcriptId": "rec-meet-8823",
            },
            engineering_evidence_json={
                "ticketId": "ENG-1042",
                "ticketTitle": "SSO rollout",
                "status": "In progress",
                "targetDelivery": "Oct 05, 2026",
                "syncedAt": "2 min ago",
                "provider": "jira",
                "ticketUrl": "https://jira.atlassian.net/browse/ENG-1042",
            },
            risk_json={
                "hasConflict": True,
                "conflictTitle": "Delivery date conflict",
                "conflictDescription": "The delivery target is 5 days after the promised date.",
                "daysDiscrepancy": 5,
            },
            recommended_step_json={
                "text": "Ask Maya to confirm the revised timeline.",
                "actionType": "draft_update",
            },
        ),
        Commitment(
            workspace_id=workspace_id,
            title="Export audit logs",
            customer_name="Northstar",
            owner_name="Daniel Stone",
            owner_email="daniel@northstar.io",
            promised_by="Sep 22, 2026",
            promised_date_iso="2026-09-22",
            status="overdue",
            status_label="Overdue",
            is_confirmed=True,
            category="needs-attention",
            quote="We will export and deliver full compliance audit logs by September 22nd.",
            original_promise_json={
                "quote": "We will export and deliver full compliance audit logs by September 22nd.",
                "sourceTitle": "Security review call",
                "timestamp": "Sep 14 · 10:15",
                "transcriptId": "rec-meet-8741",
            },
            engineering_evidence_json={
                "ticketId": "ENG-988",
                "ticketTitle": "Audit log exporter pipeline",
                "status": "Blocked",
                "targetDelivery": "Sep 24, 2026",
                "syncedAt": "15 min ago",
                "provider": "jira",
                "ticketUrl": "https://jira.atlassian.net/browse/ENG-988",
            },
            risk_json={
                "hasConflict": True,
                "conflictTitle": "Commitment overdue",
                "conflictDescription": "Promised deadline passed. Downstream customer compliance depends on this export.",
                "daysDiscrepancy": 2,
            },
            recommended_step_json={
                "text": "Send proactive delay update to Northstar compliance lead.",
                "actionType": "draft_update",
            },
        ),
        Commitment(
            workspace_id=workspace_id,
            title="Custom webhooks v2",
            customer_name="Fintech Plus",
            owner_name="Sara Connor",
            owner_email="sara@acme.corp",
            promised_by="Oct 12, 2026",
            promised_date_iso="2026-10-12",
            status="awaiting-review",
            status_label="Awaiting review",
            is_confirmed=False,
            category="awaiting-review",
            quote="Our engineering team can add custom payload signature webhooks before mid-October.",
            original_promise_json={
                "quote": "Our engineering team can add custom payload signature webhooks before mid-October.",
                "sourceTitle": "Weekly Sync - Product",
                "timestamp": "Yesterday · 16:00",
                "transcriptId": "rec-meet-9104",
            },
            engineering_evidence_json={},
            risk_json={"hasConflict": False},
            recommended_step_json={
                "text": "Review and confirm this candidate commitment.",
                "actionType": "review",
            },
        ),
        Commitment(
            workspace_id=workspace_id,
            title="Automated PDF Reports",
            customer_name="Global Logistics",
            owner_name="Maya Chen",
            owner_email="maya@acme.corp",
            promised_by="Aug 30, 2026",
            promised_date_iso="2026-08-30",
            status="delivered",
            status_label="Delivered",
            is_confirmed=True,
            category="delivered",
            quote="We will have the PDF report generation in staging and live for your team by August 30.",
            original_promise_json={
                "quote": "We will have the PDF report generation in staging and live for your team by August 30.",
                "sourceTitle": "Quarterly Business Review",
                "timestamp": "Aug 10 · 11:30",
                "transcriptId": "rec-meet-7041",
            },
            engineering_evidence_json={
                "ticketId": "ENG-870",
                "ticketTitle": "PDF report generation pipeline",
                "status": "Done",
                "targetDelivery": "Aug 29, 2026",
                "syncedAt": "Aug 29, 2026",
                "provider": "jira",
            },
            risk_json={"hasConflict": False},
            recommended_step_json={
                "text": "Commitment verified and delivered.",
                "actionType": "draft_update",
            },
        ),
    ]
        db.add_all(seeds)
        await db.commit()
        # Mark workspace as seeded permanently in Redis so future GETs skip the DB check
        if r and seeded_key:
            await r.set(seeded_key, "1")
    finally:
        # Always release the lock, even if commit fails
        if r and lock_key:
            try:
                await r.delete(lock_key)
            except Exception:
                pass  # lock auto-expires after 10s


@router.get("", response_model=PaginatedCommitmentsResponse)
async def list_commitments(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=100,
        ge=1,
        le=100,
        description="Items per page. Maximum 100. Defaults to 100 for backwards compatibility.",
    ),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieve commitments for the user's workspace with evidence and risk metrics.

    Fix #6: Enforces mandatory pagination (LIMIT + OFFSET) so no request can
    load the entire workspace table into memory. Returns PaginatedCommitmentsResponse
    with total count and has_next flag for frontend cursor advancement.
    """
    ws_id = await get_active_workspace_id(db, user)
    await _seed_default_commitments_if_empty(db, ws_id)

    # Build base filtered query (no pagination yet — used for COUNT)
    base_query = select(Commitment).where(Commitment.workspace_id == ws_id)

    if status_filter:
        base_query = base_query.where(Commitment.status == status_filter)
    if category_filter:
        base_query = base_query.where(Commitment.category == category_filter)
    if search:
        base_query = base_query.where(
            Commitment.title.ilike(f"%{search}%") | Commitment.customer_name.ilike(f"%{search}%")
        )

    # Efficient COUNT over the same filters (single DB round-trip via subquery)
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Fetch the requested page with LIMIT + OFFSET
    paged_query = (
        base_query
        .order_by(desc(Commitment.created_at))
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(paged_query)
    items = [_to_dto(c) for c in result.scalars().all()]

    return PaginatedCommitmentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.post("", response_model=CommitmentDTO, status_code=status.HTTP_201_CREATED)
async def create_commitment(
    payload: CommitmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Create a new tracked commitment."""
    ws_id = await get_active_workspace_id(db, user)

    quote_text = payload.quote or f"Commitment to deliver {payload.title}"
    owner_name = payload.owner_name or (user.full_name if user else "Lead Engineer")
    owner_email = payload.owner_email or (user.email if user else "lead@acme.corp")

    eng_evidence = {}
    if payload.ticket_id:
        eng_evidence = {
            "ticketId": payload.ticket_id,
            "ticketTitle": payload.ticket_title or payload.title,
            "status": "In progress",
            "targetDelivery": payload.promised_by or "Upcoming sprint",
            "syncedAt": "Just now",
            "provider": payload.provider,
        }

    commitment = Commitment(
        workspace_id=ws_id,
        title=payload.title,
        customer_name=payload.customer,
        owner_name=owner_name,
        owner_email=owner_email,
        promised_by=payload.promised_by or "Upcoming",
        promised_date_iso=payload.promised_date_iso or "",
        status="confirmed",
        status_label="Confirmed",
        is_confirmed=True,
        category="on-track",
        quote=quote_text,
        original_promise_json={
            "quote": quote_text,
            "sourceTitle": "Direct manual entry",
            "timestamp": "Just now",
        },
        engineering_evidence_json=eng_evidence,
        risk_json={"hasConflict": False},
        recommended_step_json={
            "text": "Monitor engineering delivery target.",
            "actionType": "draft_update",
        },
    )
    db.add(commitment)
    await record_audit_event(
        db=db,
        workspace_id=ws_id,
        actor_id=user.id if user else ws_id,
        action="COMMITMENT_CREATED",
        target_type="commitment",
        target_id=str(commitment.id),
        description=f"Created commitment '{commitment.title}' for {commitment.customer_name}.",
        payload={"promised_by": commitment.promised_by},
    )
    await db.commit()
    await db.refresh(commitment)

    await publish_event(
        f"ws:{ws_id}:events",
        "COMMITMENT_CREATED",
        {"id": str(commitment.id), "title": commitment.title, "customer": commitment.customer_name},
    )
    return _to_dto(commitment)


@router.patch("/{commitment_id}", response_model=CommitmentDTO)
async def update_commitment(
    commitment_id: uuid.UUID,
    payload: CommitmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Update title, status, or date of a commitment.

    Fix #9: Verifies the commitment belongs to the caller's workspace before
    allowing any mutation. Previously any token holder could PATCH any
    tenant's commitment by guessing the commitment UUID.
    """
    c = await db.get(Commitment, commitment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    # Ownership guard — cross-tenant write must be rejected with 403
    caller_ws_id = await get_active_workspace_id(db, user)
    if c.workspace_id != caller_ws_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this commitment.",
        )

    if payload.title is not None:
        c.title = payload.title
    if payload.customer is not None:
        c.customer_name = payload.customer
    if payload.promised_by is not None:
        c.promised_by = payload.promised_by
    if payload.status is not None:
        c.status = payload.status
        c.status_label = payload.status.replace("-", " ").capitalize()
        if payload.status == "delivered":
            c.category = "delivered"
        elif payload.status in ("at-risk", "overdue"):
            c.category = "needs-attention"
        elif payload.status == "confirmed":
            c.category = "on-track"
    if payload.is_confirmed is not None:
        c.is_confirmed = payload.is_confirmed
        if payload.is_confirmed and c.status == "awaiting-review":
            c.status = "confirmed"
            c.status_label = "Confirmed"
            c.category = "on-track"

    await record_audit_event(
        db=db,
        workspace_id=c.workspace_id,
        actor_id=c.workspace_id,
        action="COMMITMENT_UPDATED",
        target_type="commitment",
        target_id=str(c.id),
        description=f"Updated commitment '{c.title}' (status: {c.status}).",
        payload={"status": c.status, "promised_by": c.promised_by},
    )
    await db.commit()
    await db.refresh(c)

    await publish_event(
        f"ws:{c.workspace_id}:events",
        "COMMITMENT_UPDATED",
        {"id": str(c.id), "title": c.title, "status": c.status},
    )
    return _to_dto(c)


@router.post("/{commitment_id}/confirm", response_model=CommitmentDTO)
async def confirm_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Confirm a candidate commitment from the review queue into active tracking.

    Fix #9: Ownership check ensures only the owning workspace can confirm.
    """
    c = await db.get(Commitment, commitment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    caller_ws_id = await get_active_workspace_id(db, user)
    if c.workspace_id != caller_ws_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to confirm this commitment.",
        )

    c.status = "confirmed"
    c.status_label = "Confirmed"
    c.is_confirmed = True
    c.category = "on-track"

    await record_audit_event(
        db=db,
        workspace_id=c.workspace_id,
        actor_id=c.workspace_id,
        action="COMMITMENT_CONFIRMED",
        target_type="commitment",
        target_id=str(c.id),
        description=f"Confirmed promise '{c.title}' for {c.customer_name} into active tracking.",
        payload={"status": "confirmed"},
    )
    await db.commit()
    await db.refresh(c)

    await publish_event(
        f"ws:{c.workspace_id}:events",
        "COMMITMENT_CONFIRMED",
        {"id": str(c.id), "title": c.title, "customer": c.customer_name},
    )
    return _to_dto(c)


@router.post("/{commitment_id}/draft-update", response_model=DraftUpdateResponse)
async def generate_draft_update(
    commitment_id: uuid.UUID,
    payload: Optional[DraftUpdateRequest] = None,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Generate an AI-crafted transparent customer status email / message update.

    Fix #9: Ownership check — only the owning workspace can draft an update.
    """
    c = await db.get(Commitment, commitment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    caller_ws_id = await get_active_workspace_id(db, user)
    if c.workspace_id != caller_ws_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this commitment.",
        )

    recipient = (payload.recipient_name if payload and payload.recipient_name else None) or c.customer_name
    ticket_id = (c.engineering_evidence_json or {}).get("ticketId", "ENG-rollout")
    target_delivery = (c.engineering_evidence_json or {}).get("targetDelivery", c.promised_by or "mid-month")

    subject = f"Update on {c.title} for {c.customer_name}"
    body = (
        f"Hi {recipient} team,\n\n"
        f"I wanted to reach out with a quick proactive update regarding '{c.title}' "
        f"which we discussed recently (target: {c.promised_by}).\n\n"
        f"Our engineering team is actively tracking this under ticket {ticket_id}. "
        f"Current progress is aligned for delivery around {target_delivery}. "
        f"We will keep you closely informed as tests are completed on our staging environment.\n\n"
        f"Best regards,\n"
        f"{c.owner_name}\nPromiseCheck Team"
    )

    return DraftUpdateResponse(
        commitment_id=str(c.id),
        subject=subject,
        body=body,
        target_channel="email",
        action_type="draft_update",
    )


@router.delete("/{commitment_id}", status_code=status.HTTP_200_OK)
async def delete_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Delete a commitment.

    Fix #9: Verifies the commitment belongs to the caller's workspace before
    deletion. Previously any token holder could delete any tenant's commitment.
    """
    c = await db.get(Commitment, commitment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    caller_ws_id = await get_active_workspace_id(db, user)
    if c.workspace_id != caller_ws_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this commitment.",
        )

    ws_id = c.workspace_id
    c_title = c.title
    await db.delete(c)
    await record_audit_event(
        db=db,
        workspace_id=ws_id,
        actor_id=ws_id,
        action="COMMITMENT_DELETED",
        target_type="commitment",
        target_id=str(commitment_id),
        description=f"Deleted commitment '{c_title}'.",
    )
    await db.commit()

    await publish_event(
        f"ws:{ws_id}:events",
        "COMMITMENT_DELETED",
        {"id": str(commitment_id), "title": c_title},
    )
    return {"status": "deleted", "id": str(commitment_id)}
