"""Notifications and communication REST router."""

from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.iam import User, get_active_workspace_id, get_current_user
from modules.notifications.schemas import NotificationAlert, SendNotificationRequest
from modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


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
