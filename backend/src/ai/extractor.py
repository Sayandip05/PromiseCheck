"""Structured promise extraction pipeline."""

from typing import Any

from ai.client import AIClient


class PromiseExtractor:
    """Extracts candidate customer commitments from normalized transcript segments."""

    def __init__(self, ai_client: AIClient | None = None) -> None:
        self.client = ai_client or AIClient()

    async def extract_candidates(self, transcript_text: str) -> list[dict[str, Any]]:
        """Extract structured promise candidates from text."""
        # Scheduled for Phase 3 implementation
        return []
