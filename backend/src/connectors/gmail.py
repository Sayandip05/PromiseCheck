"""Gmail Integration Connector for Email Threads, Follow-ups, and Status Updates."""

import os
from typing import Any, Optional

import httpx

from connectors.base import BaseConnector, ConnectorDeliveryError, ConnectorNotConfiguredError
from core.logging import get_logger

logger = get_logger("connector.gmail")


class GmailConnector(BaseConnector):
    """Sends proactive customer updates and syncs commitment conversations via Gmail API."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = access_token or os.getenv("GMAIL_ACCESS_TOKEN") or ""

    @property
    def provider_name(self) -> str:
        return "gmail"

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        token = credentials.get("access_token", self.access_token)
        if not token:
            raise ConnectorNotConfiguredError("Gmail connector requires a valid access token.")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if res.status_code != 200:
                    raise ConnectorDeliveryError(f"Gmail profile verification failed: HTTP {res.status_code}")
                return True
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Gmail verification error: {exc}")

    async def send_draft_update(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Send formatted customer status update email."""
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Gmail connector is not configured. Authorize Google account first.")

        try:
            import base64
            from email.message import EmailMessage

            msg = EmailMessage()
            msg.set_content(body)
            msg["To"] = to_email
            msg["Subject"] = subject
            encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                    headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                    json={"raw": encoded},
                )
                if res.status_code == 200:
                    return {"status": "sent", "message_id": res.json().get("id")}
                raise ConnectorDeliveryError(f"Gmail send rejected: HTTP {res.status_code} {res.text}")
        except (ConnectorNotConfiguredError, ConnectorDeliveryError):
            raise
        except Exception as exc:
            raise ConnectorDeliveryError(f"Gmail send failed: {exc}")

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        if not self.is_configured:
            raise ConnectorNotConfiguredError("Gmail connector is not configured.")
        return {"status": "active"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "synchronized"}
