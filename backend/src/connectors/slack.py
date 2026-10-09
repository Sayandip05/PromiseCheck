"""Slack Integration Connector for Real-Time Alerts and Digests."""

import os
from typing import Any, Optional

import httpx

from connectors.base import BaseConnector, ConnectorDeliveryError, ConnectorNotConfiguredError
from core.logging import get_logger

logger = get_logger("connector.slack")


class SlackConnector(BaseConnector):
    """Sends proactive commitment alerts, deadline warnings, and updates to Slack channels."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        default_channel: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> None:
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN") or ""
        self.default_channel = default_channel or os.getenv("SLACK_ALERT_CHANNEL") or "#account-commitments"
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL") or ""

    @property
    def provider_name(self) -> str:
        return "slack"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token or self.webhook_url)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        """Verify Slack bot token against /api/auth.test."""
        token = credentials.get("bot_token", self.bot_token)
        webhook = credentials.get("webhook_url", self.webhook_url)
        if not token and not webhook:
            raise ConnectorNotConfiguredError("Slack connector requires a bot_token or webhook_url.")

        if token:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.post(
                        "https://slack.com/api/auth.test",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    data = res.json()
                    if not data.get("ok"):
                        raise ConnectorDeliveryError(f"Slack auth test failed: {data.get('error', 'invalid credentials')}")
                    return True
            except (ConnectorNotConfiguredError, ConnectorDeliveryError):
                raise
            except Exception as exc:
                raise ConnectorDeliveryError(f"Slack connection failed: {exc}")

        return True

    async def post_message(
        self,
        text: str,
        channel: Optional[str] = None,
        blocks: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Send message or rich block payload to configured Slack channel."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Slack is not configured. Supply a bot token or webhook URL.")

        target_channel = channel or self.default_channel

        # 1. Real Webhook execution if available
        if self.webhook_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(self.webhook_url, json={"text": text, "blocks": blocks})
                    if res.status_code == 200:
                        return {"status": "delivered", "provider": "slack_webhook"}
                    raise ConnectorDeliveryError(f"Slack webhook rejected payload: HTTP {res.status_code} {res.text}")
            except (ConnectorNotConfiguredError, ConnectorDeliveryError):
                raise
            except Exception as exc:
                raise ConnectorDeliveryError(f"Slack webhook delivery error: {exc}")

        # 2. Real Bot Token execution if available
        if self.bot_token:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    payload: dict[str, Any] = {"channel": target_channel, "text": text}
                    if blocks:
                        payload["blocks"] = blocks
                    res = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={"Authorization": f"Bearer {self.bot_token}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    data = res.json()
                    if data.get("ok"):
                        return {"status": "delivered", "ts": data.get("ts"), "channel": target_channel}
                    raise ConnectorDeliveryError(f"Slack chat.postMessage failed: {data.get('error', 'unknown error')}")
            except (ConnectorNotConfiguredError, ConnectorDeliveryError):
                raise
            except Exception as exc:
                raise ConnectorDeliveryError(f"Slack API error: {exc}")

        raise ConnectorNotConfiguredError("Slack connector credentials invalid or missing.")

    async def send_commitment_alert(
        self,
        title: str,
        customer: str,
        status: str,
        due_date: str,
        risk_reason: str,
    ) -> dict[str, Any]:
        """Structured alert message with formatted Slack Block Kit UI."""
        header = f"🚨 *Commitment Alert:* {title} ({customer})"
        body = (
            f"• *Status:* `{status.upper()}`\n"
            f"• *Due:* {due_date}\n"
            f"• *Risk Assessment:* {risk_reason}\n"
            f"• *Action:* Review delivery evidence in PromiseCheck dashboard."
        )
        return await self.post_message(text=f"{header}\n{body}")

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Slack is not configured.")
        return {"status": "active", "channel": self.default_channel}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "synchronized"}
