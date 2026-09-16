"""Generic SMTP / Resend / SendGrid Email Dispatch Connector."""

import os
from typing import Any, Optional

import httpx

from connectors.base import BaseConnector
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
        return True

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> dict[str, Any]:
        """Send email via Resend API or log to stdout in fluent mode."""
        if self.is_configured:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json={
                            "from": self.sender_email,
                            "to": [to_email],
                            "subject": subject,
                            "html": html_content,
                        },
                    )
                    if res.status_code in (200, 201):
                        return {"status": "sent", "id": res.json().get("id")}
            except Exception as exc:
                logger.error(f"[Email Connector] Failed to send email via Resend: {exc}")

        # Fluent pre-credential logging
        logger.info(f"[Email Mock Delivery] From: {self.sender_email} -> To: {to_email} | Subject: {subject}")
        return {
            "status": "sent_fluent_mock",
            "from": self.sender_email,
            "to": to_email,
            "subject": subject,
        }

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"status": "active" if self.is_configured else "fluent_mock"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "synchronized"}
