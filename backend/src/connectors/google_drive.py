"""Google Drive connector."""

from typing import Any

from connectors.base import BaseConnector


class GoogleDriveConnector(BaseConnector):
    """Imports authorized meeting recordings and transcript artifacts from Google Drive."""

    @property
    def provider_name(self) -> str:
        return "google_drive"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"files_imported": 0, "status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "stub"}
