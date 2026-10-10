"""Commitments domain service for business logic, status transitions, and data integrity."""

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from core.logging import get_logger
from core.redis import publish_event
from modules.audit.service import record_audit_event
from modules.commitments.models import Commitment
from modules.commitments.schemas import (
    CommitmentCreateRequest,
    CommitmentDTO,
    CommitmentUpdateRequest,
    DraftUpdateResponse,
    EngineeringEvidenceSchema,
    OriginalPromiseSchema,
    OwnerSchema,
    RecommendedStepSchema,
    RiskAnalysisSchema,
)
from modules.identity.models import User
from core.outbox.service import create_outbox_event

logger = get_logger("commitment_service")

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


def to_dto(c: Commitment) -> CommitmentDTO:
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


class CommitmentService:
    """Encapsulates commitment lifecycle operations, state transitions, and persistence."""

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        commitment_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Optional[Commitment]:
        """Fetch commitment ensuring workspace tenant isolation."""
        stmt = select(Commitment).where(
            Commitment.id == commitment_id,
            Commitment.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_commitments(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[CommitmentDTO], int]:
        """Query paginated commitments with tenant isolation and optional filtering."""
        base_query = select(Commitment).where(Commitment.workspace_id == workspace_id)

        if status_filter:
            base_query = base_query.where(Commitment.status == status_filter)
        if category_filter:
            base_query = base_query.where(Commitment.category == category_filter)
        if search:
            base_query = base_query.where(
                Commitment.title.ilike(f"%{search}%") | Commitment.customer_name.ilike(f"%{search}%")
            )

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        paged_query = (
            base_query
            .order_by(desc(Commitment.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await db.execute(paged_query)
        dtos = [to_dto(c) for c in result.scalars().all()]
        return dtos, total

    @staticmethod
    async def list_attention_commitments(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Commitment]:
        """List commitments requiring notifications or team attention."""
        stmt = (
            select(Commitment)
            .where(
                Commitment.workspace_id == workspace_id,
                Commitment.status.in_(["at-risk", "overdue", "awaiting-review"]),
            )
            .order_by(Commitment.updated_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_all_workspace_commitments(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[Commitment]:
        """Retrieve all commitments within workspace tenant boundary."""
        stmt = select(Commitment).where(Commitment.workspace_id == workspace_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_commitment(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user: Optional[User],
        payload: CommitmentCreateRequest,
    ) -> Commitment:
        """Create a new tracked commitment with atomic audit and outbox registration."""
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
            workspace_id=workspace_id,
            title=payload.title,
            customer_name=payload.customer,
            owner_name=owner_name,
            owner_email=owner_email,
            promised_by=payload.promised_by or "Upcoming",
            promised_date=payload.promised_date,
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
            workspace_id=workspace_id,
            actor_id=user.id if user else workspace_id,
            action="COMMITMENT_CREATED",
            target_type="commitment",
            target_id=str(commitment.id),
            description=f"Created commitment '{commitment.title}' for {commitment.customer_name}.",
            payload={"promised_by": commitment.promised_by},
        )

        # Atomic Outbox event recording in same DB transaction
        await create_outbox_event(
            db=db,
            workspace_id=workspace_id,
            event_type="commitment.created",
            payload={"id": str(commitment.id), "title": commitment.title, "customer": commitment.customer_name},
        )

        await db.commit()
        await db.refresh(commitment)

        # Immediate socket push for real-time live browser tabs
        await publish_event(
            f"ws:{workspace_id}:events",
            "COMMITMENT_CREATED",
            {"id": str(commitment.id), "title": commitment.title, "customer": commitment.customer_name},
        )
        return commitment

    @staticmethod
    async def update_commitment(
        db: AsyncSession,
        commitment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user: Optional[User],
        payload: CommitmentUpdateRequest,
        if_match: Optional[str] = None,
    ) -> Commitment:
        """Update commitment fields and status with optimistic concurrency control and state enforcement."""
        c = await db.get(Commitment, commitment_id)
        if not c:
            raise HTTPException(status_code=404, detail="Commitment not found")

        if c.workspace_id != workspace_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to modify this commitment.",
            )

        # OCC validation
        current_etag = f'W/"{c.id}:{int(c.updated_at.timestamp())}"'
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

        await create_outbox_event(
            db=db,
            workspace_id=c.workspace_id,
            event_type="commitment.updated",
            payload={"id": str(c.id), "title": c.title, "status": c.status},
        )

        await db.commit()
        await db.refresh(c)

        await publish_event(
            f"ws:{c.workspace_id}:events",
            "COMMITMENT_UPDATED",
            {"id": str(c.id), "title": c.title, "status": c.status},
        )
        return c

    @staticmethod
    async def confirm_commitment(
        db: AsyncSession,
        commitment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user: Optional[User],
    ) -> Commitment:
        """Confirm a candidate commitment into active tracking."""
        c = await db.get(Commitment, commitment_id)
        if not c:
            raise HTTPException(status_code=404, detail="Commitment not found")

        if c.workspace_id != workspace_id:
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

        await create_outbox_event(
            db=db,
            workspace_id=c.workspace_id,
            event_type="commitment.confirmed",
            payload={"id": str(c.id), "title": c.title, "customer": c.customer_name},
        )

        await db.commit()
        await db.refresh(c)

        await publish_event(
            f"ws:{c.workspace_id}:events",
            "COMMITMENT_CONFIRMED",
            {"id": str(c.id), "title": c.title, "customer": c.customer_name},
        )
        return c

    @staticmethod
    async def delete_commitment(
        db: AsyncSession,
        commitment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user: Optional[User],
    ) -> tuple[str, str]:
        """Delete a commitment within tenant boundary."""
        c = await db.get(Commitment, commitment_id)
        if not c:
            raise HTTPException(status_code=404, detail="Commitment not found")

        if c.workspace_id != workspace_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this commitment.",
            )

        c_title = c.title
        await db.delete(c)
        await record_audit_event(
            db=db,
            workspace_id=workspace_id,
            actor_id=user.id if user else workspace_id,
            action="COMMITMENT_DELETED",
            target_type="commitment",
            target_id=str(commitment_id),
            description=f"Deleted commitment '{c_title}'.",
        )
        await db.commit()

        await publish_event(
            f"ws:{workspace_id}:events",
            "COMMITMENT_DELETED",
            {"id": str(commitment_id), "title": c_title},
        )
        return str(commitment_id), c_title

    @staticmethod
    async def mark_delivered(
        db: AsyncSession,
        commitment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        evidence_type: str,
        evidence_title: str,
        evidence_url: Optional[str] = None,
    ) -> Optional[Commitment]:
        """Transition commitment to delivered and append verified engineering evidence."""
        c = await CommitmentService.get_by_id(db, commitment_id, workspace_id)
        if not c:
            return None

        c.status = "delivered"
        c.status_label = "Delivered"
        c.category = "delivered"
        c.is_confirmed = True

        ev_json = dict(c.engineering_evidence_json or {})
        if evidence_type == "release_notes":
            rels = list(ev_json.get("releaseNotes", []))
            rels.append(evidence_title)
            ev_json["releaseNotes"] = rels
        elif evidence_type == "pr_merged":
            prs = list(ev_json.get("prs", []))
            prs.append({
                "title": evidence_title,
                "url": evidence_url or "",
                "status": "merged",
            })
            ev_json["prs"] = prs

        c.engineering_evidence_json = ev_json
        return c

    @staticmethod
    async def generate_draft_update(
        db: AsyncSession,
        commitment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        recipient_name: Optional[str] = None,
    ) -> DraftUpdateResponse:
        """Generate an AI-crafted transparent customer status email / message update."""
        c = await CommitmentService.get_by_id(db, commitment_id, workspace_id)
        if not c:
            raise HTTPException(status_code=404, detail="Commitment not found")

        recipient = recipient_name or c.customer_name
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

    @staticmethod
    def create_candidate_commitments_batch_sync(
        session: SyncSession,
        workspace_id: str,
        candidates: list[dict[str, Any]],
        meeting_title: str,
        customer_name: str,
    ) -> int:
        """Create extracted promise candidates synchronously (reused by Celery worker)."""
        created_count = 0
        for item in candidates:
            _raw_date = item.get("promised_date_iso", "")
            _promised_date: date | None = None
            if _raw_date:
                try:
                    _promised_date = date.fromisoformat(_raw_date[:10])
                except ValueError:
                    _promised_date = None

            c = Commitment(
                workspace_id=uuid.UUID(workspace_id),
                title=item.get("title", "New commitment candidate"),
                customer_name=item.get("customer", customer_name),
                quote=item.get("quote", ""),
                promised_by=item.get("promised_by", "Upcoming"),
                promised_date=_promised_date,
                status="awaiting-review",
                status_label="Awaiting review",
                category="awaiting-review",
                is_confirmed=False,
                has_conflict=False,
                conflict_days=0,
                original_promise_json={
                    "quote": item.get("quote", ""),
                    "sourceTitle": meeting_title,
                    "timestamp": "Just now (Extracted)",
                    "context": item.get("context", ""),
                },
                risk_json={"level": "low", "reason": "New candidate awaiting verification", "conflictDays": 0},
                engineering_evidence_json={"prs": [], "tickets": [], "releaseNotes": []},
            )
            session.add(c)
            created_count += 1
        return created_count
