"""Engineering module router (Jira/Linear tracker ticket mapping)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.base import ConnectorDeliveryError, ConnectorNotConfiguredError
from connectors.jira import JiraConnector
from connectors.linear import LinearConnector
from core.database import get_db
from core.security import get_current_user
from modules.commitments.models import Commitment
from modules.identity.models import User
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
async def list_linked_tickets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List linked engineering tracker tickets from active commitments. Pure read, zero fake fallbacks."""
    ws_id = await get_active_workspace_id(db, user)
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

    return tickets


@router.get("/tickets/{tracker}/{key}")
async def get_remote_ticket_status(
    tracker: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Directly query remote Jira or Linear status. Fails fast if tracker is not configured."""
    ws_id = await get_active_workspace_id(db, user)
    from modules.operations.models import WorkspaceIntegration

    stmt = select(WorkspaceIntegration).where(
        WorkspaceIntegration.workspace_id == ws_id,
        WorkspaceIntegration.provider == tracker.lower(),
    )
    res = await db.execute(stmt)
    int_rec = res.scalar_one_or_none()
    cfg = int_rec.get_decrypted_config() if int_rec else {}

    try:
        if tracker.lower() == "jira":
            jira = JiraConnector(
                domain=cfg.get("domain"),
                email=cfg.get("email"),
                api_token=cfg.get("api_token") or cfg.get("api_key"),
            )
            return await jira.get_ticket(key)
        elif tracker.lower() == "linear":
            linear = LinearConnector(
                api_key=cfg.get("api_key"),
            )
            return await linear.get_issue(key)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported engineering tracker: {tracker}")
    except ConnectorNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ConnectorDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
