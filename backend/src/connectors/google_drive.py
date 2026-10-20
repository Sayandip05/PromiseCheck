"""Google Drive Integration Connector for Document and Presentation Search."""

import os
from typing import Any, Optional

import httpx

from connectors.connector_interface import (
    BaseConnector,
    ConnectorDeliveryError,
    ConnectorNotConfiguredError,
)
from core.logging import get_logger

logger = get_logger("connector.google_drive")


class GoogleDriveConnector(BaseConnector):
    """Searches shared Google Drive customer folders, decks, and contracts for commitment clauses."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = access_token or os.getenv("GOOGLE_ACCESS_TOKEN") or ""

    @property
    def provider_name(self) -> str:
        return "google_drive"

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        token = credentials.get("access_token", self.access_token)
        if not token:
            logger.warning("[Google Drive] No access token supplied — credentials not configured.")
            return False
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/drive/v3/about?fields=user",
                    headers={"Authorization": f"Bearer {token}"},
                )
                return res.status_code == 200
        except Exception as exc:
            logger.warning(f"[Google Drive] Token verification failed: {exc}")
            return False

    async def search_documents(self, query: str) -> list[dict[str, Any]]:
        """Search Google Drive documents matching keywords.

        Raises ``ConnectorNotConfiguredError`` when no access token is available
        and ``ConnectorDeliveryError`` when Google's API fails.  No synthetic
        documents are ever returned on behalf of an unconfigured integration.
        """
        if not self.access_token:
            raise ConnectorNotConfiguredError(
                "Google Drive is not configured; connect a Google account or set "
                "GOOGLE_ACCESS_TOKEN."
            )
        # Escape single quotes so a query cannot break out of the Drive q filter.
        safe_query = query.replace("\\", "\\\\").replace("'", "\\'")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/drive/v3/files",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params={"q": f"name contains '{safe_query}' and trashed = false"},
                )
        except httpx.HTTPError as exc:
            raise ConnectorDeliveryError(f"Google Drive search failed: {exc}") from exc

        if res.status_code != 200:
            raise ConnectorDeliveryError(
                f"Google Drive API returned HTTP {res.status_code}: {res.text[:200]}"
            )
        return res.json().get("files", [])

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        configured = await self.verify_credentials({})
        status = "active" if configured else "unconfigured"
        return {"status": status, "provider": self.provider_name}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        configured = await self.verify_credentials({})
        status = "synchronized" if configured else "unconfigured"
        return {"status": status, "provider": self.provider_name}
