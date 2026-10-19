"""Controlled External MCP Gateway.

Outbound calls to external Model Context Protocol servers are only permitted
when the server URL has been explicitly allowlisted for the workspace.  Every
request is additionally screened by the SSRF guard before any network I/O.
"""

from typing import Any, Iterable, Optional

import httpx

from connectors.connector_interface import (
    ConnectorDeliveryError,
    ConnectorNotConfiguredError,
)
from connectors.ssrf_guard import validate_no_ssrf
from core.logging import get_logger

logger = get_logger("mcp_gateway")


class MCPClientGateway:
    """Outbound client gateway to explicitly allowlisted external MCP servers."""

    def __init__(
        self,
        allowlist: Optional[Iterable[str]] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.allowlist: list[str] = [self._normalize(url) for url in (allowlist or []) if url]
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _normalize(url: str) -> str:
        return url.strip().rstrip("/")

    def is_allowed(self, server_url: str) -> bool:
        """Return True when the server URL is on the workspace allowlist."""
        return self._normalize(server_url) in self.allowlist

    async def execute_tool(
        self,
        server_url: str,
        tool_name: str,
        arguments: dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a tool on an authorized external MCP server.

        Raises:
            PermissionError: the server is not on the workspace allowlist.
            ConnectorNotConfiguredError: the server URL is missing.
            ConnectorDeliveryError: the remote server failed, timed out, or
                returned an error payload.
        """
        normalized = self._normalize(server_url or "")
        if not normalized:
            raise ConnectorNotConfiguredError(
                "External MCP server URL is required to execute a tool."
            )
        if normalized not in self.allowlist:
            raise PermissionError(
                f"External MCP server '{normalized}' is not on the workspace allowlist."
            )

        # SSRF guard raises HTTPException(400) for private/internal targets.
        validate_no_ssrf(normalized)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        logger.info("Executing external MCP tool '%s' on '%s'", tool_name, normalized)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{normalized}/tools/call",
                    headers=headers,
                    json={"name": tool_name, "arguments": arguments},
                )
        except httpx.HTTPError as exc:
            raise ConnectorDeliveryError(
                f"External MCP tool '{tool_name}' request failed on {normalized}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise ConnectorDeliveryError(
                f"External MCP server returned HTTP {response.status_code} for "
                f"tool '{tool_name}': {response.text[:200]}"
            )

        payload = response.json()
        if isinstance(payload, dict) and payload.get("error"):
            raise ConnectorDeliveryError(
                f"External MCP server rejected tool '{tool_name}': {payload['error']}"
            )
        return payload
