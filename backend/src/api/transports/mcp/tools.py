"""Model Context Protocol (MCP) stateless tool implementations for AI agents.

All tools now accept an explicit workspace_id forwarded by the authenticated
server.py router.  This ensures every DB query is scoped to the calling user's
tenant and prevents cross-tenant data access.
"""

import uuid
from typing import Any, Optional

from core.database import AsyncSessionLocal
from modules.commitments import CommitmentCreateRequest, CommitmentService, RiskService


async def _resolve_workspace(workspace_id: Optional[str]) -> uuid.UUID:
    """Parse and return the workspace UUID, raising ValueError on bad input."""
    if workspace_id:
        return uuid.UUID(workspace_id)
    raise ValueError("workspace_id is required for all MCP tool calls")


async def list_commitments_tool(
    status: Optional[str] = None,
    customer: Optional[str] = None,
    limit: int = 50,
    workspace_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retrieve tracked commitments filtered by status or customer for AI context.

    Always scoped to the caller's workspace — no cross-tenant rows returned.
    """
    ws_uuid = await _resolve_workspace(workspace_id)

    async with AsyncSessionLocal() as db:
        items, _ = await CommitmentService.list_commitments(
            db=db,
            workspace_id=ws_uuid,
            status_filter=status,
            search=customer,
            page=1,
            page_size=min(limit, 100),
        )
        return [
            {
                "id": d.id,
                "title": d.title,
                "customer": d.customer,
                "status": d.status,
                "status_label": d.statusLabel,
                "promised_by": d.promisedBy,
                "promised_date": d.promisedDateIso,
                "is_confirmed": d.isConfirmed,
                "category": d.category,
                "owner": d.owner.model_dump() if d.owner else None,
                "original_promise": d.originalPromise.model_dump() if d.originalPromise else None,
                "engineering_evidence": (
                    d.engineeringEvidence.model_dump() if d.engineeringEvidence else None
                ),
                "risk": d.risk.model_dump() if d.risk else None,
            }
            for d in items
        ]


async def get_commitment_evidence_tool(
    commitment_id: str,
    workspace_id: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieve full transcript quote, source context, and Jira ticket evidence.

    Enforces workspace ownership — returns 403-equivalent error if the
    commitment does not belong to the caller's workspace.
    """
    try:
        c_uuid = uuid.UUID(commitment_id)
    except ValueError:
        return {"error": "Invalid commitment UUID format"}

    ws_uuid = await _resolve_workspace(workspace_id)

    async with AsyncSessionLocal() as db:
        c = await CommitmentService.get_by_id(db, ws_uuid, c_uuid)
        if not c:
            return {"error": f"Commitment '{commitment_id}' not found"}

        return {
            "id": str(c.id),
            "title": c.title,
            "customer": c.customer_name,
            "owner": {"name": c.owner_name, "email": c.owner_email},
            "promised_by": c.promised_by,
            "promised_date": c.promised_date.isoformat() if c.promised_date else None,
            "status": c.status,
            "has_conflict": c.has_conflict,
            "conflict_days": c.conflict_days,
            "ticket_id": c.ticket_id,
            "ticket_status": c.ticket_status,
            "original_promise": c.original_promise_json or {"quote": c.quote},
            "engineering_evidence": c.engineering_evidence_json or {},
            "risk_analysis": c.risk_json or {},
        }


async def create_commitment_tool(
    title: str,
    customer: str,
    quote: str,
    promised_by: str,
    workspace_id: Optional[str] = None,
) -> dict[str, Any]:
    """AI agent tool to register a newly detected commitment in the caller's workspace."""
    ws_uuid = await _resolve_workspace(workspace_id)

    async with AsyncSessionLocal() as db:
        payload = CommitmentCreateRequest(
            title=title,
            customer=customer,
            quote=quote,
            promised_by=promised_by,
            owner_name="AI Agent",
            owner_email="agent@promisecheck.io",
        )
        commitment = await CommitmentService.create_commitment(
            db=db,
            workspace_id=ws_uuid,
            user=None,
            payload=payload,
        )
        return {
            "status": "created",
            "id": str(commitment.id),
            "workspace_id": str(commitment.workspace_id),
            "title": commitment.title,
            "customer": commitment.customer_name,
        }


async def create_update_draft_tool(
    commitment_id: str,
    proposed_message: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> dict[str, Any]:
    """Generate or stage an update draft message requiring human approval.

    Validates workspace ownership before generating the draft.
    """
    try:
        c_uuid = uuid.UUID(commitment_id)
    except ValueError:
        return {"error": "Invalid commitment UUID format"}

    ws_uuid = await _resolve_workspace(workspace_id)

    async with AsyncSessionLocal() as db:
        c = await CommitmentService.get_by_id(db, ws_uuid, c_uuid)
        if not c:
            return {"error": f"Commitment '{commitment_id}' not found"}

        body = (
            proposed_message
            or f"Hi {c.customer_name} team, quick status update regarding '{c.title}' (target: {c.promised_by}). Delivery is on track."
        )

        return {
            "status": "draft_created",
            "commitment_id": str(c.id),
            "customer": c.customer_name,
            "draft_body": body,
            "requires_approval": True,
        }


async def investigate_commitment_tool(
    commitment_id: str,
    workspace_id: Optional[str] = None,
) -> dict[str, Any]:
    """Investigate delivery risk for a commitment with a bounded tool-using agent.

    Cross-references the linked Jira/Linear ticket when configured and returns
    structured findings plus a recommended mitigation step.  Scoped to the
    caller's workspace.
    """
    try:
        c_uuid = uuid.UUID(commitment_id)
    except ValueError:
        return {"error": "Invalid commitment UUID format"}

    ws_uuid = await _resolve_workspace(workspace_id)

    async with AsyncSessionLocal() as db:
        return await RiskService.investigate_commitment(db, ws_uuid, c_uuid)


# Tool Definitions for MCP Discovery Protocol
MCP_TOOLS_MANIFEST = [
    {
        "name": "list_commitments",
        "description": "List customer commitments with status, deadlines, and delivery risk.",
        "required_scope": "commitments:read",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status: at-risk, overdue, confirmed, delivered, awaiting-review"},
                "customer": {"type": "string", "description": "Filter by customer name"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "get_commitment_evidence",
        "description": "Fetch quote, meeting transcript snippet, and Jira/Linear ticket linkage for a commitment.",
        "required_scope": "evidence:read",
        "inputSchema": {
            "type": "object",
            "required": ["commitment_id"],
            "properties": {
                "commitment_id": {"type": "string", "description": "UUID of the commitment"},
            },
        },
    },
    {
        "name": "investigate_commitment",
        "description": (
            "Investigate delivery risk for a commitment, cross-referencing linked "
            "Jira/Linear tickets and returning a recommended mitigation step."
        ),
        "required_scope": "risk:read",
        "inputSchema": {
            "type": "object",
            "required": ["commitment_id"],
            "properties": {
                "commitment_id": {"type": "string", "description": "UUID of the commitment"},
            },
        },
    },
    {
        "name": "create_commitment",
        "description": "Create a new customer commitment record (placed in awaiting-review queue).",
        "required_scope": "commitments:write",
        "inputSchema": {
            "type": "object",
            "required": ["title", "customer", "quote", "promised_by"],
            "properties": {
                "title": {"type": "string"},
                "customer": {"type": "string"},
                "quote": {"type": "string"},
                "promised_by": {"type": "string"},
            },
        },
    },
    {
        "name": "create_update_draft",
        "description": "Draft a proactive status update message for human review and approval.",
        "required_scope": "drafts:write",
        "inputSchema": {
            "type": "object",
            "required": ["commitment_id"],
            "properties": {
                "commitment_id": {"type": "string"},
                "proposed_message": {"type": "string"},
            },
        },
    },
]
