"""Notifications and communication router."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.base import ConnectorDeliveryError, ConnectorNotConfiguredError
from connectors.email import EmailConnector
from connectors.slack import SlackConnector
from core.database import get_db
from core.security import get_current_user
from modules.commitments.models import Commitment
from modules.identity.models import User
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
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List recent notification and alert events using indexed SQL query."""
    ws_id = await get_active_workspace_id(db, user)
    stmt = (
        select(Commitment)
        .where(
            Commitment.workspace_id == ws_id,
            Commitment.status.in_(["at-risk", "overdue", "awaiting-review"]),
        )
        .order_by(Commitment.updated_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    commitments = result.scalars().all()

    alerts: list[NotificationAlert] = []
    for c in commitments:
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
async def send_notification(
    payload: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dispatch real-time notification alert via Slack, Gmail, or Email connector."""
    ws_id = await get_active_workspace_id(db, user)
    try:
        if payload.channel.lower() == "slack":
            from modules.operations.models import WorkspaceIntegration

            stmt_int = select(WorkspaceIntegration).where(
                WorkspaceIntegration.workspace_id == ws_id,
                WorkspaceIntegration.provider == "slack",
            )
            res_int = await db.execute(stmt_int)
            slack_int = res_int.scalar_one_or_none()
            cfg = slack_int.get_decrypted_config() if slack_int else {}
            slack = SlackConnector(
                bot_token=cfg.get("bot_token") or cfg.get("api_key"),
                default_channel=payload.recipient or cfg.get("channel") or cfg.get("scope"),
                webhook_url=cfg.get("webhook_url"),
            )
            res = await slack.post_message(
                text=payload.message or "Commitment SLA update from PromiseCheck",
                channel=payload.recipient or cfg.get("channel"),
            )
            return {"status": "dispatched", "channel": "slack", "result": res}
        elif payload.channel.lower() in ("email", "gmail"):
            from connectors.google_auth import get_valid_google_token_for_workspace
            from connectors.gmail import GmailConnector

            access_token, sender_email = await get_valid_google_token_for_workspace(db, ws_id)
            if access_token:
                gmail_conn = GmailConnector(access_token=access_token)
                res = await gmail_conn.send_draft_update(
                    to_email=payload.recipient or "team@acme.corp",
                    subject="PromiseCheck Delivery Alert",
                    body=payload.message or "Commitment status update.",
                )
                return {"status": "dispatched", "channel": "gmail", "sender": sender_email, "result": res}
            else:
                email_conn = EmailConnector()
                res = await email_conn.send_email(
                    to_email=payload.recipient or "team@acme.corp",
                    subject="PromiseCheck Delivery Alert",
                    html_content=f"<p>{payload.message}</p>",
                )
                return {"status": "dispatched", "channel": "email", "result": res}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported notification channel: {payload.channel}")
    except ConnectorNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ConnectorDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
