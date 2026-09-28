"""Hosted LLM API client — Groq only. Raises RuntimeError on any failure."""

from typing import Optional

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger("ai_client")


class AIClient:
    """Thin wrapper around the Groq chat-completions API.

    Only Groq is supported.  If the API key is missing, the HTTP call fails,
    or the response is empty/unexpected, a ``RuntimeError`` is raised so that
    callers (FastAPI endpoints) can return HTTP 503 and Celery tasks can retry.
    """

    def __init__(
        self,
        provider: str = settings.LLM_PROVIDER,
        model: str = settings.LLM_MODEL,
    ) -> None:
        self.provider = provider or "groq"
        self.model = model or "llama-3.3-70b-versatile"
        self.groq_api_key = (
            settings.GROQ_API_KEY
            or settings.LLM_API_KEY
            or ""
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Groq chat-completions API (async).

        Raises:
            RuntimeError: if GROQ_API_KEY is missing, the HTTP call fails,
                          the status code is not 200, or the returned text is empty.
        """
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured — cannot call LLM")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info(f"Calling Groq LLM API with model: {self.model}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1500,
                },
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Groq API returned HTTP {response.status_code}: {response.text[:300]}"
            )

        text = response.json()["choices"][0]["message"]["content"]
        if not text or not text.strip():
            raise RuntimeError("Groq API returned an empty response")

        return text

    def generate_sync(self, prompt: str, system_prompt: str | None = None) -> str:
        """Blocking Groq call for Celery worker context (no asyncio event loop).

        Raises:
            RuntimeError: same conditions as :meth:`generate`.
        """
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured — cannot call LLM")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info(f"[Celery] Calling Groq LLM (sync) with model: {self.model}")
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1500,
                },
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"[Celery] Groq API returned HTTP {response.status_code}: {response.text[:300]}"
            )

        text = response.json()["choices"][0]["message"]["content"]
        if not text or not text.strip():
            raise RuntimeError("[Celery] Groq API returned an empty response")

        return text
