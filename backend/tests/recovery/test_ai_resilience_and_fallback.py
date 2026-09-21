"""Tests for Groq LLM extraction and fail-fast behavior (no NLP fallback)."""

from unittest.mock import AsyncMock
import pytest

from ai.extractor import PromiseExtractor


@pytest.mark.asyncio
async def test_empty_transcript_handling():
    """Verify that empty or whitespace-only transcripts return empty list safely."""
    extractor = PromiseExtractor()
    assert await extractor.extract_candidates("") == []
    assert await extractor.extract_candidates("   \n\t  ") == []


@pytest.mark.asyncio
async def test_groq_successful_extraction():
    """Verify structured promise extraction when Groq returns valid JSON."""
    mock_client = AsyncMock()
    mock_client.generate.return_value = (
        '[{"title": "Deploy SSO integration", "quote": "We will deploy SSO by next Friday.", '
        '"customer": "Acme", "promised_by": "Next Friday", "promised_date_iso": "2026-10-02", "confidence": 0.95}]'
    )
    extractor = PromiseExtractor(ai_client=mock_client)
    sample_text = "We will deploy the single sign-on integration by next Friday."
    results = await extractor.extract_candidates(sample_text)
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Deploy SSO integration"
    assert results[0]["customer"] == "Acme"


@pytest.mark.asyncio
async def test_llm_api_failure_fails_fast():
    """Verify that when Groq LLM throws errors, extractor raises RuntimeError without falling back."""
    mock_client = AsyncMock()
    mock_client.generate.side_effect = ConnectionError("Groq API unreachable or timed out")

    extractor = PromiseExtractor(ai_client=mock_client)
    sample_text = "We will deliver the audit logging feature by end of sprint."

    # Must raise RuntimeError — no heuristic NLP fallback
    with pytest.raises(RuntimeError) as exc_info:
        await extractor.extract_candidates(sample_text)
    assert "Groq LLM extraction failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_llm_response_fails_fast():
    """Verify that invalid/malformed JSON returned by LLM raises RuntimeError (fail fast)."""
    mock_client = AsyncMock()
    mock_client.generate.return_value = "Sorry, I am an AI and cannot format this as JSON: [unclosed list"

    extractor = PromiseExtractor(ai_client=mock_client)
    sample_text = "We will release the multi-tenant dashboard by November 15."

    with pytest.raises(RuntimeError) as exc_info:
        await extractor.extract_candidates(sample_text)
    assert "Groq LLM extraction failed" in str(exc_info.value)
