"""Engineering module REST router (Jira/Linear tracker ticket mapping)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.iam.dependencies import get_current_user
from modules.commitments.tickets.service import EngineeringService
from modules.iam.models import User
from modules.iam.service import get_active_workspace_id

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
    """List linked engineering tracker tickets from active commitments."""
    ws_id = await get_active_workspace_id(db, user)
    tickets = await EngineeringService.list_linked_tickets(db, ws_id)
    return [TicketSnapshot(**t) for t in tickets]


@router.get("/tickets/{tracker}/{key}")
async def get_remote_ticket_status(
    tracker: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Directly query remote Jira or Linear status via EngineeringService."""
    ws_id = await get_active_workspace_id(db, user)
    return await EngineeringService.get_remote_ticket_status(db, ws_id, tracker, key)
