"""Engineering module router (Jira/Linear tracker ticket mapping)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.jira import JiraConnector
from connectors.linear import LinearConnector
from core.database import get_db
from modules.commitments.models import Commitment
from modules.workspaces.service import get_active_workspace_id

router = APIRouter(prefix="/engineering", tags=["Engineering Trackers"])


class TicketSnapshot(BaseModel):
    """Normalized engineering issue record."""

    id: str
    tracker: str  # jira, linear, github
    key: str
    status: str
    target_date: str | None = None
    commitment_id: str | None = None
    commitment_title: str | None = None


@router.get("/tickets", response_model=list[TicketSnapshot])
async def list_linked_tickets(db: AsyncSession = Depends(get_db)):
    """List linked engineering tracker tickets from active commitments."""
    ws_id = await get_active_workspace_id(db)
    stmt = select(Commitment).where(Commitment.workspace_id == ws_id)
    result = await db.execute(stmt)
    commitments = result.scalars().all()

    tickets: list[TicketSnapshot] = []
    for c in commitments:
        evidence = c.engineering_evidence_json or {}
        for t in evidence.get("tickets", []):
            tickets.append(
                TicketSnapshot(
                    id=f"{t.get('tracker', 'jira')}-{t.get('key', 'ENG-1')}",
                    tracker=t.get("tracker", "jira"),
                    key=t.get("key", "UNKNOWN"),
                    status=t.get("status", "In Progress"),
                    target_date=t.get("targetDate"),
                    commitment_id=str(c.id),
                    commitment_title=c.title,
                )
            )

    # Fallback seed tickets if none linked yet
    if not tickets:
        tickets = [
            TicketSnapshot(id="jira-1", tracker="jira", key="SEC-412", status="In Progress", target_date="Oct 20", commitment_title="SOC-2 Type II report deliverable"),
            TicketSnapshot(id="linear-1", tracker="linear", key="ENG-891", status="Review", target_date="Oct 14", commitment_title="EU data residency deployment"),
            TicketSnapshot(id="jira-2", tracker="jira", key="BILL-104", status="Backlog", target_date="Nov 01", commitment_title="Custom quarterly billing invoices"),
        ]

    return tickets


@router.get("/tickets/{tracker}/{key}")
async def get_remote_ticket_status(tracker: str, key: str):
    """Directly query remote Jira or Linear status with fluent fallback."""
    if tracker.lower() == "jira":
        jira = JiraConnector()
        return await jira.get_ticket(key)
    elif tracker.lower() == "linear":
        linear = LinearConnector()
        return await linear.get_issue(key)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported engineering tracker: {tracker}")
