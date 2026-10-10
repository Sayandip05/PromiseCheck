"""Commitments REST router with full lifecycle, evidence tracking, and AI drafting."""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.redis import get_async_redis
from core.security import get_current_user
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
import json
from modules.workspaces.service import get_active_workspace_id
from core.redis import publish_event
from modules.audit.service import record_audit_event
from core.logging import get_logger

logger = get_logger("commitments_router")
router = APIRouter(prefix="/commitments", tags=["Commitments"])

# ---------------------------------------------------------------------------
# State transitions matrix and category synchronization
# ---------------------------------------------------------------------------
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "awaiting-review": {"awaiting-review", "confirmed", "at-risk", "blocked", "canceled", "superseded"},
    "confirmed": {"confirmed", "at-risk", "overdue", "blocked", "delivered", "canceled", "superseded"},
    "at-risk": {"at-risk", "confirmed", "overdue", "blocked", "delivered", "canceled", "superseded"},
    "overdue": {"overdue", "confirmed", "at-risk", "blocked", "delivered", "canceled", "superseded"},
    "blocked": {"blocked", "confirmed", "at-risk", "overdue", "delivered", "canceled", "superseded"},
    "delivered": {"delivered"},    # Terminal: cannot arbitrarily reopen
    "canceled": {"canceled"},      # Terminal
    "superseded": {"superseded"},  # Terminal
}

STATUS_CATEGORY_MAP: dict[str, str] = {
    "awaiting-review": "awaiting-review",
    "confirmed": "on-track",
    "at-risk": "needs-attention",
    "overdue": "needs-attention",
    "blocked": "needs-attention",
    "delivered": "delivered",
    "superseded": "superseded",
    "canceled": "canceled",
}



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
        # Serialise the Date column to an ISO string for the frontend contract.
        promisedDateIso=c.promised_date.isoformat() if c.promised_date else "",
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
    user: User = Depends(get_current_user),
):
    """Retrieve commitments for the user's workspace with evidence and risk metrics. Pure idempotent read."""
    ws_id = await get_active_workspace_id(db, user)

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
    user: User = Depends(get_current_user),
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
        promised_date=payload.promised_date,
        # Populate first-class ticket columns from the incoming payload
        ticket_id=payload.ticket_id,
        ticket_status="In progress" if payload.ticket_id else None,
        has_conflict=False,
        conflict_days=0,
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


@router.get("/{commitment_id}", response_model=CommitmentDTO)
async def get_commitment(
    commitment_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve an individual commitment by UUID with workspace tenancy authorization."""
    c = await db.get(Commitment, commitment_id)
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")

    caller_ws_id = await get_active_workspace_id(db, user)
    if c.workspace_id != caller_ws_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this commitment.",
        )

    response.headers["ETag"] = f'W/"{c.id}:{int(c.updated_at.timestamp())}"'
    return _to_dto(c)


@router.patch("/{commitment_id}", response_model=CommitmentDTO)
async def update_commitment(
    commitment_id: uuid.UUID,
    payload: CommitmentUpdateRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update title, status, or date of a commitment with optimistic concurrency control.

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

    # Optimistic Concurrency Control (OCC) via If-Match / ETag
    current_etag = f'W/"{c.id}:{int(c.updated_at.timestamp())}"'
    if_match = request.headers.get("if-match")
    if if_match and if_match.strip() not in (current_etag, "*"):
        logger.warning(
            f"[occ] 412 Precondition Failed for commitment={c.id}. "
            f"Client If-Match='{if_match}' does not match current ETag='{current_etag}'"
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Precondition Failed: Resource has been modified concurrently. Please reload latest state.",
        )

    if payload.title is not None:
        c.title = payload.title
    if payload.customer is not None:
        c.customer_name = payload.customer
    if payload.promised_by is not None:
        c.promised_by = payload.promised_by
    if payload.status is not None:
        allowed = VALID_STATUS_TRANSITIONS.get(c.status, {c.status})
        if payload.status not in allowed:
            logger.warning(
                f"[commitments] 422 Invalid status transition rejected for commitment={c.id}: "
                f"'{c.status}' -> '{payload.status}'"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status transition from '{c.status}' to '{payload.status}'.",
            )
        c.status = payload.status
        c.status_label = payload.status.replace("-", " ").capitalize()
        c.category = STATUS_CATEGORY_MAP.get(payload.status, c.category)
        if payload.status == "delivered":
            c.is_confirmed = True

    if payload.is_confirmed is not None:
        c.is_confirmed = payload.is_confirmed
        if payload.is_confirmed and c.status == "awaiting-review":
            c.status = "confirmed"
            c.status_label = "Confirmed"
            c.category = "on-track"

    await record_audit_event(
        db=db,
        workspace_id=c.workspace_id,
        actor_id=user.id if user else c.workspace_id,
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
    response.headers["ETag"] = f'W/"{c.id}:{int(c.updated_at.timestamp())}"'
    return _to_dto(c)


@router.post("/{commitment_id}/confirm", response_model=CommitmentDTO)
async def confirm_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
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
        actor_id=user.id if user else c.workspace_id,
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
    user: User = Depends(get_current_user),
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

    try:
        from ai.client import AIClient
        ai_client = AIClient()
        system_prompt = (
            "You are an expert customer communications specialist for PromiseCheck. "
            "Draft a transparent, evidence-grounded status update email regarding a customer commitment. "
            "Output valid JSON with keys 'subject' and 'body' only."
        )
        prompt = (
            f"Commitment: {c.title}\n"
            f"Customer: {c.customer_name}\n"
            f"Recipient: {recipient}\n"
            f"Promised Date / Horizon: {c.promised_by}\n"
            f"Current Status: {c.status}\n"
            f"Linked Ticket: {ticket_id}\n"
            f"Target Delivery: {target_delivery}\n"
            f"Owner: {c.owner_name}\n\n"
            "Produce an authentic, polished update email as a JSON object."
        )
        raw_response = await ai_client.generate(prompt=prompt, system_prompt=system_prompt)
        if raw_response:
            clean = raw_response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            try:
                data = json.loads(clean.strip())
                if isinstance(data, dict):
                    if data.get("subject"):
                        subject = str(data["subject"]).strip()
                    if data.get("body"):
                        body = str(data["body"]).strip()
            except Exception:
                if clean:
                    body = clean
    except Exception as exc:
        logger.warning(f"AI draft generation error, using fallback template: {exc}")

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
    user: User = Depends(get_current_user),
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
        actor_id=user.id if user else ws_id,
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
