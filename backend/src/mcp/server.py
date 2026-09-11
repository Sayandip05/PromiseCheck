"""Authenticated PromiseCheck MCP Server."""

from core.logging import get_logger

logger = get_logger("mcp_server")


class MCPServer:
    """PromiseCheck MCP server exposing permission-filtered tools to authorized AI clients."""

    def __init__(self) -> None:
        self.is_running = False

    def start(self) -> None:
        """Start server over stream or HTTP transport (Phase 7)."""
        logger.info("Initializing PromiseCheck MCP server")
        self.is_running = True


mcp_server = MCPServer()
