"""Hosted LLM API client supporting Groq (primary) and Gemini (fallback)."""

import json
import os
from typing import Optional

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger("ai_client")


class AIClient:
    """Interface to configured LLM provider: Groq as primary, Gemini as fallback."""

    def __init__(
        self,
        provider: str = settings.LLM_PROVIDER,
        model: str = settings.LLM_MODEL,
    ) -> None:
        self.provider = provider or "groq"
        self.model = model or "llama-3.3-70b-versatile"
        self.groq_api_key = (
            settings.GROQ_API_KEY
            or os.getenv("GROQ_API_KEY")
            or settings.LLM_API_KEY
            or os.getenv("LLM_API_KEY")
            or ""
        )
        self.gemini_api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or ""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute LLM generation via Groq API, falling back to Gemini if available."""
        # 1. Primary: Groq API
        if self.groq_api_key:
            try:
                logger.info(f"Calling Groq LLM API with model: {self.model}")
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

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
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.warning(
                            f"Groq API returned status {response.status_code}: {response.text}"
                        )
            except Exception as e:
                logger.error(f"Error calling Groq API: {e}")

        # 2. Fallback: Google Gemini API
        if self.gemini_api_key:
            try:
                logger.info("Falling back to Google Gemini Flash API")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                payload = {"contents": [{"parts": [{"text": full_prompt}]}]}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")

        # 3. Deterministic local extractor fallback
        logger.info("Using local deterministic AI fallback")
        return ""
