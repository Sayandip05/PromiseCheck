"""Hosted LLM API client wrapper."""

from core.config import settings
from core.logging import get_logger

logger = get_logger("ai_client")


class AIClient:
    """Interface to configured LLM provider (Anthropic, OpenAI, etc.)."""

    def __init__(
        self, provider: str = settings.LLM_PROVIDER, model: str = settings.LLM_MODEL
    ) -> None:
        self.provider = provider
        self.model = model

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call LLM API with cost limits and retry handling (Phase 3)."""
        logger.info(f"Generating completion via {self.provider}:{self.model}")
        return "Stubbed LLM response"
