"""Stateless Model Context Protocol (MCP) Server and Router."""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.logging import get_logger
from modules.mcp.tools import (
    MCP_TOOLS_MANIFEST,
    create_commitment_tool,
    create_update_draft_tool,
    get_commitment_evidence_tool,
    list_commitments_tool,
)

logger = get_logger("mcp_server")
mcp_router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])

# Native FastMCP Server instance for STDIO and SSE MCP clients
try:
    from fastmcp import FastMCP
    mcp_app = FastMCP(name="PromiseCheck MCP Server")

    @mcp_app.tool()
    async def list_commitments(status: Optional[str] = None, customer: Optional[str] = None, limit: int = 50) -> dict:
        """List customer commitments tracked in PromiseCheck with status, evidence, and risk."""
        return await list_commitments_tool(status=status, customer=customer, limit=limit)

    @mcp_app.tool()
    async def get_commitment_evidence(commitment_id: str) -> dict:
        """Retrieve linked engineering evidence (PRs, commits, release notes) for a commitment."""
        return await get_commitment_evidence_tool(commitment_id=commitment_id)

    @mcp_app.tool()
    async def create_commitment(title: str, customer: str, quote: str = "", promised_by: str = "Upcoming") -> dict:
        """Record a new customer promise or commitment."""
        return await create_commitment_tool(title=title, customer=customer, quote=quote, promised_by=promised_by)

    @mcp_app.tool()
    async def create_update_draft(commitment_id: str, proposed_message: Optional[str] = None) -> dict:
        """Generate a professional customer-facing update draft for a commitment."""
        return await create_update_draft_tool(commitment_id=commitment_id, proposed_message=proposed_message)
except Exception as e:
    logger.warning(f"FastMCP server initialization warning: {e}")
    mcp_app = None


class CallToolRequest(BaseModel):
    """MCP standard tool execution request."""

    name: str
    arguments: dict[str, Any] = {}


class CallToolResponse(BaseModel):
    """MCP standard tool execution response."""

    content: list[dict[str, Any]]
    isError: bool = False


@mcp_router.get("/tools")
async def list_mcp_tools():
    """MCP standard endpoint: return discovery manifest of all tools."""
    return {"tools": MCP_TOOLS_MANIFEST}


@mcp_router.post("/tools/call", response_model=CallToolResponse)
async def call_mcp_tool(request: CallToolRequest):
    """MCP standard endpoint: execute a tool statelessly and return content."""
    tool_name = request.name
    args = request.arguments

    logger.info(f"MCP tool invocation: {tool_name} with args {args}")

    try:
        if tool_name == "list_commitments":
            data = await list_commitments_tool(
                status=args.get("status"),
                customer=args.get("customer"),
                limit=args.get("limit", 50),
            )
        elif tool_name == "get_commitment_evidence":
            commitment_id = args.get("commitment_id")
            if not commitment_id:
                raise HTTPException(status_code=400, detail="Missing required argument 'commitment_id'")
            data = await get_commitment_evidence_tool(commitment_id)
        elif tool_name == "create_commitment":
            data = await create_commitment_tool(
                title=args.get("title", "New Commitment"),
                customer=args.get("customer", "Customer"),
                quote=args.get("quote", ""),
                promised_by=args.get("promised_by", "Upcoming"),
            )
        elif tool_name == "create_update_draft":
            commitment_id = args.get("commitment_id")
            if not commitment_id:
                raise HTTPException(status_code=400, detail="Missing required argument 'commitment_id'")
            data = await create_update_draft_tool(
                commitment_id=commitment_id,
                proposed_message=args.get("proposed_message"),
            )
        else:
            raise HTTPException(status_code=404, detail=f"Unknown tool: '{tool_name}'")

        import json
        return CallToolResponse(
            content=[{"type": "text", "text": json.dumps(data, indent=2, default=str)}],
            isError=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing MCP tool '{tool_name}': {e}")
        return CallToolResponse(
            content=[{"type": "text", "text": f"Tool execution failed: {str(e)}"}],
            isError=True,
        )
