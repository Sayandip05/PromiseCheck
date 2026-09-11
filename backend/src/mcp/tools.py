"""Model Context Protocol (MCP) tool declarations."""

from typing import Any


def list_commitments_tool(workspace_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve commitments for authorized external AI clients."""
    return []


def get_commitment_evidence_tool(commitment_id: str) -> dict[str, Any]:
    """Retrieve verified quote and source evidence for a commitment."""
    return {}


def create_update_draft_tool(commitment_id: str, proposed_message: str) -> dict[str, Any]:
    """Save an update draft requiring explicit human review before sending."""
    return {"status": "draft_created", "requires_approval": True}
