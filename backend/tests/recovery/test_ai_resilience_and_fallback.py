"""Resilience tests for Groq LLM failure modes, malformed responses, and regex NLP fallback."""

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
async def test_deterministic_nlp_fallback_extraction():
    """Verify deterministic NLP extracts commitments when LLM is bypassed."""
    extractor = PromiseExtractor()
    sample_text = (
        "During the product sync, the engineering lead confirmed: "
        "We will deploy the single sign-on integration by next Friday. "
        "The customer agreed this satisfies their enterprise requirements."
    )
    results = extractor._deterministic_extract(sample_text)
    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    assert "title" in first
    assert "quote" in first
    assert "promised_by" in first


@pytest.mark.asyncio
async def test_llm_api_failure_fallback_resilience():
    """Verify that when Groq LLM throws connection errors, the extractor falls back gracefully."""
    mock_client = AsyncMock()
    mock_client.generate.side_effect = ConnectionError("Groq API unreachable or timed out")

    extractor = PromiseExtractor(ai_client=mock_client)
    sample_text = "We will deliver the audit logging feature by end of sprint."

    # Must NOT raise ConnectionError, must fall back to deterministic NLP
    results = await extractor.extract_candidates(sample_text)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "audit logging" in results[0]["title"].lower() or "deliver" in results[0]["quote"].lower()


@pytest.mark.asyncio
async def test_malformed_llm_response_resilience():
    """Verify that invalid/malformed JSON returned by LLM does not crash the pipeline."""
    mock_client = AsyncMock()
    mock_client.generate.return_value = "Sorry, I am an AI and cannot format this as JSON: [unclosed list"

    extractor = PromiseExtractor(ai_client=mock_client)
    sample_text = "We will release the multi-tenant dashboard by November 15."

    results = await extractor.extract_candidates(sample_text)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "dashboard" in results[0]["title"].lower() or "release" in results[0]["quote"].lower()
