"""Notifications domain service for alert generation and multi-channel delivery."""

import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.connector_interface import ConnectorDeliveryError, ConnectorNotConfiguredError
from connectors.email import EmailConnector
from connectors.slack import SlackConnector
from modules.commitments.service import CommitmentService
from modules.integrations.service import IntegrationService


class NotificationService:
    """Encapsulates notification alert generation, channel dispatch, and connector handling."""

    @staticmethod
    async def list_alerts(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """List active deadline and review alerts for commitments requiring attention."""
        commitments = await CommitmentService.list_attention_commitments(db, workspace_id, limit=50)
        alerts: list[dict[str, Any]] = []
        for c in commitments:
            alerts.append({
                "id": f"alert-{str(c.id)[:8]}",
                "commitment_id": str(c.id),
                "commitment_title": c.title,
                "channel": "slack",
                "recipient": c.owner_email or "#account-updates",
                "status": "pending_approval" if c.status == "awaiting-review" else "sent",
                "alert_message": f"Commitment for {c.customer_name} is currently {c.status}. Due: {c.promised_by or 'Soon'}.",
            })
        return alerts

    @staticmethod
    async def send_alert(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        channel: str,
        recipient: Optional[str],
        message: str,
    ) -> dict[str, Any]:
        """Dispatch real-time notification alert via Slack, Gmail, or Email connector."""
        try:
            if channel.lower() == "slack":
                cfg = await IntegrationService.get_decrypted_config(db, workspace_id, "slack")
                slack = SlackConnector(
                    bot_token=cfg.get("bot_token") or cfg.get("api_key"),
                    default_channel=recipient or cfg.get("channel") or cfg.get("scope"),
                    webhook_url=cfg.get("webhook_url"),
                )
                res = await slack.post_message(
                    text=message or "Commitment SLA update from PromiseCheck",
                    channel=recipient or cfg.get("channel"),
                )
                return {"status": "dispatched", "channel": "slack", "result": res}

            elif channel.lower() in ("email", "gmail"):
                from modules.integrations.service import get_valid_google_token_for_workspace
                from connectors.gmail import GmailConnector

                access_token, sender_email = await get_valid_google_token_for_workspace(db, workspace_id)
                if access_token:
                    gmail_conn = GmailConnector(access_token=access_token)
                    res = await gmail_conn.send_draft_update(
                        to_email=recipient or "team@acme.corp",
                        subject="PromiseCheck Delivery Alert",
                        body=message or "Commitment status update.",
                    )
                    return {"status": "dispatched", "channel": "gmail", "sender": sender_email, "result": res}
                else:
                    email_conn = EmailConnector()
                    res = await email_conn.send_email(
                        to_email=recipient or "team@acme.corp",
                        subject="PromiseCheck Delivery Alert",
                        html_content=f"<p>{message}</p>",
                    )
                    return {"status": "dispatched", "channel": "email", "result": res}
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported notification channel: {channel}")

        except ConnectorNotConfiguredError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except ConnectorDeliveryError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
