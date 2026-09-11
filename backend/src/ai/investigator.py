"""Bounded investigation agent."""

from typing import Any

from ai.client import AIClient


class InvestigationAgent:
    """Bounded tool-using agent that checks Jira/Linear dates and drafts customer updates."""

    def __init__(self, max_tool_calls: int = 6) -> None:
        self.max_tool_calls = max_tool_calls
        self.client = AIClient()

    async def investigate_commitment(self, commitment_id: str) -> dict[str, Any]:
        """Run tool loop within safety budget (Phase 7)."""
        return {"status": "investigation_stub", "tool_calls_used": 0}
