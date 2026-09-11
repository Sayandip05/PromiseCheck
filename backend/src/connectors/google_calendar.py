"""Google Calendar connector."""

from typing import Any

from connectors.base import BaseConnector


class GoogleCalendarConnector(BaseConnector):
    """Discovers upcoming meetings and synchronizes schedule updates."""

    @property
    def provider_name(self) -> str:
        return "google_calendar"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"events_synced": 0, "status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "stub"}
