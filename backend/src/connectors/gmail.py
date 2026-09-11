"""Gmail connector."""

from typing import Any

from connectors.base import BaseConnector


class GmailConnector(BaseConnector):
    """Synchronizes selected email message threads to capture written customer commitments."""

    @property
    def provider_name(self) -> str:
        return "gmail"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"threads_synced": 0, "status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "stub"}
