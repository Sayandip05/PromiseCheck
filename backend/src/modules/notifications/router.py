"""Notifications and communication REST router."""

from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from modules.iam.models import User
from modules.notifications.service import NotificationService
from modules.iam.service import get_active_workspace_id

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


class NotificationAlert(BaseModel):
    """Internal Slack/Email delivery alert."""

    id: str
    commitment_id: str
    commitment_title: str
    channel: str  # slack, email
    recipient: str
    status: str  # pending_approval, sent, scheduled
    alert_message: str


class SendNotificationRequest(BaseModel):
    """Request payload to dispatch an alert."""

    commitment_id: Optional[str] = None
    channel: str = "slack"  # slack | email
    recipient: Optional[str] = None
    message: str = ""


@router.get("", response_model=list[NotificationAlert])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List recent notification and alert events via NotificationService."""
    ws_id = await get_active_workspace_id(db, user)
    alerts = await NotificationService.list_alerts(db, ws_id)
    return [NotificationAlert(**a) for a in alerts]


@router.post("/send", status_code=status.HTTP_200_OK)
async def send_notification(
    payload: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dispatch real-time notification alert via Slack, Gmail, or Email connector."""
    ws_id = await get_active_workspace_id(db, user)
    return await NotificationService.send_alert(
        db=db,
        workspace_id=ws_id,
        channel=payload.channel,
        recipient=payload.recipient,
        message=payload.message,
    )
