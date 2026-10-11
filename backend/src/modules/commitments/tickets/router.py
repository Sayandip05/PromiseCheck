"""Engineering module REST router (Jira/Linear tracker ticket mapping)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.commitments.tickets.schemas import TicketSnapshot
from modules.commitments.tickets.service import EngineeringService
from modules.iam import User, get_active_workspace_id, get_current_user

router = APIRouter(prefix="/engineering", tags=["Engineering Trackers"])


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
