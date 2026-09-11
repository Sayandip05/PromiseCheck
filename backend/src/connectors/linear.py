"""Linear integration connector."""

from typing import Any

from connectors.base import BaseConnector


class LinearConnector(BaseConnector):
    """Synchronizes engineering issues and cycles from Linear GraphQL API."""

    @property
    def provider_name(self) -> str:
        return "linear"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        # Scheduled for Phase 5 implementation
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"issues_synced": 0, "status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"issues_reconciled": 0, "status": "stub"}
