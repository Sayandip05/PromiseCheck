"""Controlled External MCP Gateway."""

from typing import Any

from core.logging import get_logger

logger = get_logger("mcp_gateway")


class MCPClientGateway:
    """Outbound client gateway to explicitly allowlisted external MCP servers."""

    def __init__(self, allowlist: list[str] | None = None) -> None:
        self.allowlist = allowlist or []

    async def execute_tool(
        self, server_url: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool on an authorized external MCP server."""
        if server_url not in self.allowlist:
            raise PermissionError(
                f"External MCP server '{server_url}' is not on the workspace allowlist."
            )
        logger.info(f"Executing external MCP tool '{tool_name}' on '{server_url}'")
        return {"result": "stub"}
