"""Commitments Pydantic DTO schemas aligned with frontend contract."""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class OwnerSchema(BaseModel):
    name: str = "Maya Chen"
    initials: str = "MC"
    avatarColor: str = "bg-neutral-200 text-neutral-800"
    email: str = "maya@acme.corp"


class OriginalPromiseSchema(BaseModel):
    quote: str
    sourceTitle: str = "Customer Onboarding"
    timestamp: str = "Just now"
    transcriptId: Optional[str] = None


class EngineeringEvidenceSchema(BaseModel):
    ticketId: str = "ENG-1042"
    ticketTitle: str = "Feature delivery rollout"
    status: str = "In progress"
    targetDelivery: str = "Oct 05, 2026"
    syncedAt: str = "Just now"
    provider: str = "jira"  # jira | linear
    ticketUrl: Optional[str] = None


class RiskAnalysisSchema(BaseModel):
    hasConflict: bool = False
    conflictTitle: Optional[str] = None
    conflictDescription: Optional[str] = None
    daysDiscrepancy: Optional[int] = None


class RecommendedStepSchema(BaseModel):
    text: str = "Review commitment details"
    actionType: str = "draft_update"  # draft_update | review | remind_owner


class CommitmentDTO(BaseModel):
    """Full commitment payload matching frontend Commitment interface."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    customer: str
    owner: OwnerSchema
    promisedBy: str
    promisedDateIso: str
    status: str  # at-risk | overdue | blocked | confirmed | delivered | awaiting-review
    statusLabel: str
    isConfirmed: bool
    category: str  # needs-attention | awaiting-review | on-track | delivered
    originalPromise: OriginalPromiseSchema
    engineeringEvidence: Optional[EngineeringEvidenceSchema] = None
    risk: Optional[RiskAnalysisSchema] = None
    recommendedNextStep: Optional[RecommendedStepSchema] = None


class PaginatedCommitmentsResponse(BaseModel):
    """Paginated wrapper for commitment list responses.

    Fix #6: Enforces a hard cap (max 100 items per page) so a single request
    can never load an entire workspace's commitment table into memory.
    """
    items: list[CommitmentDTO]
    total: int              # total matching rows across all pages
    page: int               # current page (1-indexed)
    page_size: int          # items returned in this page
    has_next: bool          # whether a subsequent page exists


class CommitmentCreateRequest(BaseModel):
    """Payload to record a new commitment."""

    title: str
    customer: str = "Acme"
    quote: str = ""
    promised_by: str = ""
    promised_date_iso: str = ""
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    ticket_id: Optional[str] = None
    ticket_title: Optional[str] = None
    provider: str = "jira"


class CommitmentUpdateRequest(BaseModel):
    """Payload to edit or transition status of a commitment."""

    title: Optional[str] = None
    customer: Optional[str] = None
    status: Optional[str] = None
    is_confirmed: Optional[bool] = None
    promised_by: Optional[str] = None
    due_date: Optional[str] = None


class DraftUpdateRequest(BaseModel):
    """Payload requesting an AI-generated proactive customer update."""

    recipient_name: Optional[str] = None
    tone: str = "empathetic_transparent"


class DraftUpdateResponse(BaseModel):
    """Generated update message draft."""

    commitment_id: str
    subject: str
    body: str
    target_channel: str = "email"
    action_type: str = "draft_update"
