"""Model Context Protocol (MCP) stateless tool implementations for AI agents."""

import uuid
from typing import Any, Optional
from sqlalchemy import select

from core.database import AsyncSessionLocal
from modules.commitments.models import Commitment
from modules.customers.models import Customer


async def list_commitments_tool(
    status: Optional[str] = None,
    customer: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve tracked commitments filtered by status or customer for AI context."""
    async with AsyncSessionLocal() as db:
        query = select(Commitment)
        if status:
            query = query.where(Commitment.status == status)
        if customer:
            query = query.where(Commitment.customer_name.ilike(f"%{customer}%"))
        query = query.limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "title": c.title,
                "customer": c.customer_name,
                "status": c.status,
                "status_label": c.status_label,
                "promised_by": c.promised_by,
                "is_confirmed": c.is_confirmed,
                "quote": c.quote,
                "engineering_evidence": c.engineering_evidence_json,
                "risk": c.risk_json,
            }
            for c in items
        ]


async def get_commitment_evidence_tool(commitment_id: str) -> dict[str, Any]:
    """Retrieve full transcript quote, source context, and Jira ticket evidence."""
    try:
        c_uuid = uuid.UUID(commitment_id)
    except ValueError:
        return {"error": "Invalid commitment UUID format"}

    async with AsyncSessionLocal() as db:
        c = await db.get(Commitment, c_uuid)
        if not c:
            return {"error": f"Commitment '{commitment_id}' not found"}

        return {
            "id": str(c.id),
            "title": c.title,
            "customer": c.customer_name,
            "owner": {"name": c.owner_name, "email": c.owner_email},
            "promised_by": c.promised_by,
            "status": c.status,
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
    """AI agent tool to register a newly detected commitment."""
    from modules.workspaces.service import get_active_workspace_id

    async with AsyncSessionLocal() as db:
        if workspace_id:
            try:
                ws_uuid = uuid.UUID(workspace_id)
            except ValueError:
                ws_uuid = await get_active_workspace_id(db)
        else:
            ws_uuid = await get_active_workspace_id(db)

        commitment = Commitment(
            workspace_id=ws_uuid,
            title=title,
            customer_name=customer,
            owner_name="AI Agent",
            owner_email="agent@promisecheck.io",
            promised_by=promised_by,
            status="confirmed",
            status_label="Confirmed",
            is_confirmed=True,
            category="on-track",
            quote=quote,
            original_promise_json={
                "quote": quote,
                "sourceTitle": "Autonomous AI Ingestion",
                "timestamp": "Just now",
            },
            engineering_evidence_json={},
            risk_json={"hasConflict": False},
        )
        db.add(commitment)
        await db.commit()
        await db.refresh(commitment)
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
) -> dict[str, Any]:
    """Generate or stage an update draft message requiring human approval."""
    try:
        c_uuid = uuid.UUID(commitment_id)
    except ValueError:
        return {"error": "Invalid commitment UUID format"}

    async with AsyncSessionLocal() as db:
        c = await db.get(Commitment, c_uuid)
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


# Tool Definitions for MCP Discovery Protocol
MCP_TOOLS_MANIFEST = [
    {
        "name": "list_commitments",
        "description": "List customer commitments with status, deadlines, and delivery risk.",
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
        "description": "Create a new customer commitment record.",
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
        "description": "Draft a proactive status update message for human review.",
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
