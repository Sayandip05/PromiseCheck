"""Notifications and communication router."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


class NotificationAlert(BaseModel):
    """Internal Slack/Email delivery alert."""

    id: str
    channel: str  # slack, email
    recipient: str
    status: str  # pending_approval, sent, failed


@router.get("", response_model=list[NotificationAlert])
async def list_notifications():
    """List recent notification and alert events."""
    return []
