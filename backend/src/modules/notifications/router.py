"""Notifications and communication router."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.email import EmailConnector
from connectors.slack import SlackConnector
from core.database import get_db
from modules.commitments.models import Commitment
from modules.workspaces.service import get_active_workspace_id

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
async def list_notifications(db: AsyncSession = Depends(get_db)):
    """List recent notification and alert events."""
    ws_id = await get_active_workspace_id(db)
    stmt = select(Commitment).where(Commitment.workspace_id == ws_id)
    result = await db.execute(stmt)
    commitments = result.scalars().all()

    alerts: list[NotificationAlert] = []
    for c in commitments:
        if c.status in ("at-risk", "overdue", "awaiting-review"):
            alerts.append(
                NotificationAlert(
                    id=f"alert-{str(c.id)[:8]}",
                    commitment_id=str(c.id),
                    commitment_title=c.title,
                    channel="slack",
                    recipient=c.owner_email or "#account-updates",
                    status="pending_approval" if c.status == "awaiting-review" else "sent",
                    alert_message=f"Commitment for {c.customer_name} is currently {c.status}. Due: {c.promised_by or 'Soon'}.",
                )
            )

    return alerts


@router.post("/send", status_code=status.HTTP_200_OK)
async def send_notification(payload: SendNotificationRequest):
    """Dispatch real-time notification alert via Slack or Email connector."""
    if payload.channel.lower() == "slack":
        slack = SlackConnector()
        res = await slack.post_message(
            text=payload.message or "Commitment SLA update from PromiseCheck",
            channel=payload.recipient,
        )
        return {"status": "dispatched", "channel": "slack", "result": res}
    elif payload.channel.lower() == "email":
        email_conn = EmailConnector()
        res = await email_conn.send_email(
            to_email=payload.recipient or "team@acme.corp",
            subject="PromiseCheck Delivery Alert",
            html_content=f"<p>{payload.message}</p>",
        )
        return {"status": "dispatched", "channel": "email", "result": res}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported notification channel: {payload.channel}")
