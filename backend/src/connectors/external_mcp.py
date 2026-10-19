"""External Model Context Protocol (MCP) Client Gateway Connector.

Connects to an explicitly authorized external MCP server.  There are no mock
tools or simulated results: an unconfigured connector raises
``ConnectorNotConfiguredError`` and provider failures raise
``ConnectorDeliveryError``.
"""

import os
from typing import Any, Optional

import httpx

from connectors.connector_interface import (
    BaseConnector,
    ConnectorDeliveryError,
    ConnectorNotConfiguredError,
)
from connectors.ssrf_guard import validate_no_ssrf
from core.logging import get_logger

logger = get_logger("connector.external_mcp")


class ExternalMCPConnector(BaseConnector):
    """Client gateway connecting to authorized external MCP servers (HTTP/SSE)."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> None:
        # ``endpoint`` is the name used by persisted integration configs;
        # ``endpoint_url`` is the explicit constructor argument used by callers.
        self.endpoint_url = endpoint_url or endpoint or os.getenv("EXTERNAL_MCP_URL") or ""
        self.auth_token = auth_token or ""

    @property
    def provider_name(self) -> str:
        return "external_mcp"

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint_url)

    def _resolve_url(self, endpoint_url: Optional[str] = None) -> str:
        url = endpoint_url or self.endpoint_url
        if not url:
            raise ConnectorNotConfiguredError(
                "External MCP is not configured; set an endpoint URL or EXTERNAL_MCP_URL."
            )
        return url

    def _headers(self) -> dict[str, str]:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    @staticmethod
    def _parse_tools(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            tools = payload.get("tools", [])
            if isinstance(tools, list):
                return [item for item in tools if isinstance(item, dict)]
        return []

    async def verify_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate connectivity to the remote MCP server."""
        url = credentials.get("endpoint_url") or credentials.get("endpoint") or self.endpoint_url
        if not url:
            return False
        validate_no_ssrf(url)  # SSRF guard: block private/internal IPs (raises HTTPException)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{url.rstrip('/')}/tools", headers=self._headers())
                return res.status_code == 200
        except httpx.HTTPError as exc:
            logger.warning(f"[External MCP] Connectivity test to {url} failed: {exc}")
            return False

    async def list_tools(self, endpoint_url: Optional[str] = None) -> list[dict[str, Any]]:
        """Query the tool discovery manifest from the remote MCP server."""
        url = self._resolve_url(endpoint_url)
        validate_no_ssrf(url)  # SSRF guard: block private/internal IPs (raises HTTPException)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{url.rstrip('/')}/tools", headers=self._headers())
        except httpx.HTTPError as exc:
            raise ConnectorDeliveryError(
                f"External MCP tool discovery failed for {url}: {exc}"
            ) from exc

        if res.status_code != 200:
            raise ConnectorDeliveryError(
                f"External MCP server returned HTTP {res.status_code} while listing tools"
            )
        return self._parse_tools(res.json())

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        endpoint_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a tool on the remote MCP server and return its result."""
        url = self._resolve_url(endpoint_url)
        validate_no_ssrf(url)  # SSRF guard: block private/internal IPs (raises HTTPException)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{url.rstrip('/')}/tools/call",
                    headers=self._headers(),
                    json={"name": tool_name, "arguments": arguments},
                )
        except httpx.HTTPError as exc:
            raise ConnectorDeliveryError(
                f"External MCP tool '{tool_name}' invocation failed on {url}: {exc}"
            ) from exc

        if res.status_code != 200:
            raise ConnectorDeliveryError(
                f"External MCP server returned HTTP {res.status_code} for tool '{tool_name}': "
                f"{res.text[:200]}"
            )

        payload = res.json()
        if isinstance(payload, dict) and payload.get("error"):
            raise ConnectorDeliveryError(
                f"External MCP server rejected tool '{tool_name}': {payload['error']}"
            )
        return payload

    async def initial_sync(self, workspace_id: str, resource_id: str) -> dict[str, Any]:
        tools = await self.list_tools()
        return {"tools_discovered": len(tools), "tools": tools, "status": "connected"}

    async def reconcile(self, workspace_id: str) -> dict[str, Any]:
        tools = await self.list_tools()
        return {"status": "synchronized", "tools_count": len(tools)}
