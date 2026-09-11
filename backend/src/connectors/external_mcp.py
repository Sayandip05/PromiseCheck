"""External MCP client gateway connector."""

from typing import Any

from connectors.base import BaseConnector


class ExternalMCPConnector(BaseConnector):
    """Client gateway connecting to explicitly authorized external MCP servers."""

    @property
    def provider_name(self) -> str:
        return "external_mcp"

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        return True

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        return {"tools_discovered": 0, "status": "stub"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        return {"status": "stub"}
