"""Generic SMTP / Resend / SendGrid Email Dispatch Connector."""

import os
from typing import Any, Optional

import httpx

from connectors.connector_interface import (
    BaseConnector,
    ConnectorDeliveryError,
    ConnectorNotConfiguredError,
)
from core.logging import get_logger

logger = get_logger("connector.email")


class EmailConnector(BaseConnector):
    """Dispatches notifications, invite emails, and customer commitment updates via SMTP or Resend API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("RESEND_API_KEY") or os.getenv("EMAIL_API_KEY") or ""
        self.sender_email = os.getenv("EMAIL_FROM") or "notifications@promisecheck.com"

    @property
    def provider_name(self) -> str:
        return "email"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        key = credentials.get("api_key", self.api_key)
        if not key:
            logger.warning("[Email] No API key supplied — credentials not configured.")
            return False
        return True

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> dict[str, Any]:
        """Send an email through the Resend API.

        Raises ``ConnectorNotConfiguredError`` when no API key is available and
        ``ConnectorDeliveryError`` when Resend rejects or fails the request.  A
        notification is never reported as sent unless the provider accepted it.
        """
        if not self.api_key:
            raise ConnectorNotConfiguredError(
                "Email is not configured; set RESEND_API_KEY or EMAIL_API_KEY."
            )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self.sender_email,
                        "to": [to_email],
                        "subject": subject,
                        "html": html_content,
                    },
                )
        except httpx.HTTPError as exc:
            raise ConnectorDeliveryError(f"Email delivery request failed: {exc}") from exc

        if res.status_code not in (200, 201):
            raise ConnectorDeliveryError(
                f"Resend API returned HTTP {res.status_code}: {res.text[:200]}"
            )
        payload = res.json()
        return {
            "status": "sent",
            "id": payload.get("id"),
            "from": self.sender_email,
            "to": to_email,
            "subject": subject,
        }

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        configured = await self.verify_credentials({})
        status = "active" if configured else "unconfigured"
        return {"status": status, "provider": self.provider_name}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        configured = await self.verify_credentials({})
        status = "synchronized" if configured else "unconfigured"
        return {"status": status, "provider": self.provider_name}
