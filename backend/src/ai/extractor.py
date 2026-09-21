"""Structured promise extraction pipeline using Groq LLM."""

import json
from typing import Any, Optional

from ai.client import AIClient
from core.logging import get_logger

logger = get_logger("promise_extractor")

SYSTEM_PROMPT = """You are an expert AI auditor for PromiseCheck.
Your task is to analyze conversational transcripts, customer meeting notes, or emails, and identify explicit commitments, deliverables, or promises made to a customer.

For each promise detected, extract:
- title: Short summary of the commitment (e.g. "Deliver SOC2 Type II Report")
- quote: The exact sentence or verbatim phrase containing the promise
- customer: The customer or client company name mentioned or implied (default: "Customer")
- promised_by: The promised delivery date/timeline mentioned (e.g. "Sep 30, 2026", "Next Friday", "End of Q3")
- promised_date_iso: Best estimate ISO date string (YYYY-MM-DD) if available, or empty string
- confidence: Float score between 0.0 and 1.0

Output ONLY a valid JSON array of objects. Do not include markdown code block formatting or explanation."""


class PromiseExtractor:
    """Extracts candidate customer commitments from transcripts and conversation text."""

    def __init__(self, ai_client: Optional[AIClient] = None) -> None:
        self.client = ai_client or AIClient()

    async def extract_candidates(self, transcript_text: str) -> list[dict[str, Any]]:
        """Extract structured promise candidates from text using Groq LLM.

        Groq LLM is the exclusive extraction engine. If Groq is unreachable or fails,
        raises a RuntimeError immediately without heuristic fallback.
        """
        if not transcript_text or not transcript_text.strip():
            return []

        prompt = f"Transcript Content:\n\"\"\"\n{transcript_text[:4000]}\n\"\"\"\n\nExtract all customer commitments as JSON array."
        try:
            raw_llm_response = await self.client.generate(prompt, system_prompt=SYSTEM_PROMPT)
            if not raw_llm_response:
                raise RuntimeError("Groq LLM returned an empty response.")

            # Clean any markdown fences if present
            clean_json_text = raw_llm_response.strip()
            if clean_json_text.startswith("```json"):
                clean_json_text = clean_json_text[7:]
            if clean_json_text.startswith("```"):
                clean_json_text = clean_json_text[3:]
            if clean_json_text.endswith("```"):
                clean_json_text = clean_json_text[:-3]

            parsed = json.loads(clean_json_text.strip())
            if not isinstance(parsed, list):
                raise ValueError("LLM response did not contain a JSON array.")

            logger.info(f"Groq successfully extracted {len(parsed)} commitments")
            return parsed
        except Exception as err:
            logger.error(f"Groq LLM extraction failed: {err}")
            raise RuntimeError(f"Groq LLM extraction failed: {err}") from err

    def extract_candidates_sync(
        self,
        transcript_text: str,
        meeting_title: str = "Meeting Sync",
        default_customer: str = "Acme",
    ) -> list[dict[str, Any]]:
        """Synchronous commitment extractor for Celery worker context.

        Calls generate_sync() (blocking httpx.Client). Groq LLM is the exclusive
        extraction engine; fails immediately if unavailable.
        """
        if not transcript_text or not transcript_text.strip():
            return []

        prompt = (
            f"Transcript Content:\n\"\"\"\n{transcript_text[:4000]}\n\"\"\"\n\n"
            "Extract all customer commitments as JSON array."
        )
        try:
            raw_response = self.client.generate_sync(prompt, system_prompt=SYSTEM_PROMPT)
            if not raw_response:
                raise RuntimeError("Groq LLM returned an empty response.")

            clean = raw_response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]

            parsed = json.loads(clean.strip())
            if not isinstance(parsed, list):
                raise ValueError("LLM response did not contain a JSON array.")

            logger.info(f"[Celery] Groq sync extracted {len(parsed)} commitments")
            return parsed
        except Exception as err:
            logger.error(f"[Celery] Sync Groq LLM extraction failed: {err}")
            raise RuntimeError(f"Groq LLM extraction failed: {err}") from err

