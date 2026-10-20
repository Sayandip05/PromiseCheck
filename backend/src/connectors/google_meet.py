"""Google Meet Integration Connector for Meeting Video, Notes, and Recording Sync."""

import os
from typing import Any, Optional

import httpx

from connectors.connector_interface import (
    BaseConnector,
    ConnectorDeliveryError,
    ConnectorNotConfiguredError,
)
from core.logging import get_logger

logger = get_logger("connector.google_meet")


class GoogleMeetConnector(BaseConnector):
    """Integrates with Google Meet to sync conference calls, transcripts, and attendee metadata."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = access_token or os.getenv("GOOGLE_ACCESS_TOKEN") or ""

    @property
    def provider_name(self) -> str:
        return "google_meet"

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        token = credentials.get("access_token", self.access_token)
        if not token:
            logger.warning("[Google Meet] No access token supplied — credentials not configured.")
            return False
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/oauth2/v1/tokeninfo",
                    params={"access_token": token},
                )
                return res.status_code == 200
        except Exception as exc:
            logger.warning(f"[Google Meet] Token verification failed: {exc}")
            return False

    async def list_recent_meetings(self) -> list[dict[str, Any]]:
        """List recent conference records from Google Meet.

        Raises ``ConnectorNotConfiguredError`` when no access token is available
        and ``ConnectorDeliveryError`` when Google's API fails.  There is no
        fabricated fallback data: an unconfigured integration must surface as
        such so callers can prompt the user to connect Google.
        """
        if not self.access_token:
            raise ConnectorNotConfiguredError(
                "Google Meet is not configured; connect a Google account or set "
                "GOOGLE_ACCESS_TOKEN."
            )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://meet.googleapis.com/v2/conferenceRecords",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
        except httpx.HTTPError as exc:
            raise ConnectorDeliveryError(
                f"Google Meet conference records request failed: {exc}"
            ) from exc

        if res.status_code != 200:
            raise ConnectorDeliveryError(
                f"Google Meet API returned HTTP {res.status_code}: {res.text[:200]}"
            )
        return res.json().get("conferenceRecords", [])

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        meetings = await self.list_recent_meetings()
        return {"meetings_synced": len(meetings), "status": "active"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        meetings = await self.list_recent_meetings()
        return {"status": "synchronized", "meetings_seen": len(meetings)}
