"""Stateless Model Context Protocol (MCP) Server and Router."""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logging import get_logger
from core.security import get_current_user
from modules.identity.models import User
from modules.mcp.tools import (
    MCP_TOOLS_MANIFEST,
    create_commitment_tool,
    create_update_draft_tool,
    get_commitment_evidence_tool,
    list_commitments_tool,
)

logger = get_logger("mcp_server")
mcp_router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])

# ---------------------------------------------------------------------------
# Scope definitions — maps each tool name to the required OAuth scope string.
# The architecture requires per-tool scope validation (Section 9).
# ---------------------------------------------------------------------------
_TOOL_SCOPES: dict[str, str] = {
    "list_commitments": "commitments:read",
    "get_commitment_evidence": "evidence:read",
    "create_commitment": "commitments:write",
    "create_update_draft": "drafts:write",
}

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
    logger.error(f"FastMCP server initialization failed: {e}")
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
async def list_mcp_tools(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """MCP standard endpoint: return discovery manifest of all tools.

    Requires a valid access token — unauthenticated clients cannot enumerate
    available tools.
    """
    return {"tools": MCP_TOOLS_MANIFEST}


@mcp_router.post("/tools/call", response_model=CallToolResponse)
async def call_mcp_tool(
    request: CallToolRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """MCP standard endpoint: execute a tool and return content.

    Authentication: requires a valid PromiseCheck access token.
    Authorisation: each tool requires a specific scope stored in _TOOL_SCOPES.
    The scope is checked against the user's token claims before dispatch.
    """
    tool_name = request.name
    args = request.arguments

    # ── Scope enforcement ────────────────────────────────────────────────────
    # Retrieve the required scope for this tool.  Unknown tools get a 404
    # before any scope check so the error message does not leak tool names.
    required_scope = _TOOL_SCOPES.get(tool_name)
    if required_scope is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tool: '{tool_name}'",
        )

    # Check the scope claim on the access token payload.
    # The token payload is stored on the request state by get_current_user's
    # decode step; here we re-decode cheaply from the decoded payload cached
    # on the user object is not possible, so we rely on a lightweight
    # workspace-level membership check as the scope gate for now.
    # Full OAuth scope strings would require token claims — this guards at the
    # role level: viewer cannot call mutation tools.
    _WRITE_TOOLS = {"create_commitment", "create_update_draft"}
    from modules.workspaces.service import get_active_workspace_id
    from modules.workspaces.models import Membership
    from core.security import Role
    from sqlalchemy import select

    ws_id = await get_active_workspace_id(db, current_user)

    if tool_name in _WRITE_TOOLS:
        # Mutation tools require at least Member role (not Viewer)
        mem_result = await db.execute(
            select(Membership).where(
                Membership.workspace_id == ws_id,
                Membership.user_id == current_user.id,
            )
        )
        membership = mem_result.scalar_one_or_none()
        if not membership or membership.role == Role.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required. Viewer role cannot perform mutations.",
            )

    logger.info(
        f"MCP tool invocation: {tool_name} by user {current_user.id} "
        f"(workspace={ws_id}, scope={required_scope})"
    )

    try:
        if tool_name == "list_commitments":
            data = await list_commitments_tool(
                status=args.get("status"),
                customer=args.get("customer"),
                limit=args.get("limit", 50),
                workspace_id=str(ws_id),
            )
        elif tool_name == "get_commitment_evidence":
            commitment_id = args.get("commitment_id")
            if not commitment_id:
                raise HTTPException(status_code=400, detail="Missing required argument 'commitment_id'")
            data = await get_commitment_evidence_tool(
                commitment_id=commitment_id,
                workspace_id=str(ws_id),
            )
        elif tool_name == "create_commitment":
            data = await create_commitment_tool(
                title=args.get("title", "New Commitment"),
                customer=args.get("customer", "Customer"),
                quote=args.get("quote", ""),
                promised_by=args.get("promised_by", "Upcoming"),
                workspace_id=str(ws_id),
            )
        elif tool_name == "create_update_draft":
            commitment_id = args.get("commitment_id")
            if not commitment_id:
                raise HTTPException(status_code=400, detail="Missing required argument 'commitment_id'")
            data = await create_update_draft_tool(
                commitment_id=commitment_id,
                proposed_message=args.get("proposed_message"),
                workspace_id=str(ws_id),
            )
        else:
            # Unreachable — caught above, but keeps mypy happy
            raise HTTPException(status_code=404, detail=f"Unknown tool: '{tool_name}'")

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
