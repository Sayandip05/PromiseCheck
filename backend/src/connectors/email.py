"""Email delivery connector for approved notifications."""

from typing import Any

from connectors.base import BaseConnector


class EmailConnector(BaseConnector):
    """Dispatches approved customer updates and internal alerts via SMTP / SendGrid / Postmark."""

    @property
    def provider_name(self) -> str:
        return "email"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "stub"}
