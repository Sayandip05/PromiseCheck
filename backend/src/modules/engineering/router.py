"""Engineering module router (Jira/Linear tracker ticket mapping)."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/engineering", tags=["Engineering Trackers"])


class TicketSnapshot(BaseModel):
    """Normalized engineering issue record."""

    id: str
    tracker: str  # jira, linear
    key: str
    status: str
    target_date: str | None = None


@router.get("/tickets", response_model=list[TicketSnapshot])
async def list_linked_tickets():
    """List linked engineering tracker tickets."""
    return []
