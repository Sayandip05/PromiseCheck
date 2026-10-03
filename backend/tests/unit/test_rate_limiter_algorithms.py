"""Unit tests for Token Bucket and Sliding Window rate limiting algorithms."""

import asyncio
import time
import pytest
from core.rate_limiter import (
    SlidingWindowLimiter,
    TokenBucketLimiter,
    RateLimitResult,
    _InMemorySlidingWindowStore,
    _InMemoryTokenBucketStore,
)


@pytest.mark.asyncio
async def test_sliding_window_in_memory_burst_and_recovery():
    """Verify in-memory sliding window allows up to max_requests and rejects excess."""
    store = _InMemorySlidingWindowStore()
    key = "test:sw:user1"

    # Allow 3 requests in a 2-second window
    r1 = await store.evaluate(key, max_requests=3, window_seconds=2)
    assert r1.allowed is True
    assert r1.remaining == 2

    r2 = await store.evaluate(key, max_requests=3, window_seconds=2)
    assert r2.allowed is True
    assert r2.remaining == 1

    r3 = await store.evaluate(key, max_requests=3, window_seconds=2)
    assert r3.allowed is True
    assert r3.remaining == 0

    # 4th request must be rejected
    r4 = await store.evaluate(key, max_requests=3, window_seconds=2)
    assert r4.allowed is False
    assert r4.retry_after >= 1


@pytest.mark.asyncio
async def test_token_bucket_in_memory_burst_and_refill():
    """Verify in-memory token bucket consumes capacity and refills over time."""
    store = _InMemoryTokenBucketStore()
    key = "test:tb:user1"

    # Capacity 2 tokens, refills 2 tokens/sec
    r1 = await store.evaluate(key, capacity=2, refill_rate=2.0, cost=1)
    assert r1.allowed is True
    assert r1.remaining == 1

    r2 = await store.evaluate(key, capacity=2, refill_rate=2.0, cost=1)
    assert r2.allowed is True
    assert r2.remaining == 0

    # Bucket empty
    r3 = await store.evaluate(key, capacity=2, refill_rate=2.0, cost=1)
    assert r3.allowed is False
    assert r3.retry_after >= 1

    # Wait 0.6s to refill at least 1 token
    await asyncio.sleep(0.6)
    r4 = await store.evaluate(key, capacity=2, refill_rate=2.0, cost=1)
    assert r4.allowed is True


@pytest.mark.asyncio
async def test_sliding_window_limiter_interface():
    """Verify SlidingWindowLimiter returns standard RateLimitResult structure."""
    limiter = SlidingWindowLimiter(max_requests=10, window_seconds=30)
    result = await limiter.is_allowed("client-ip-test-1")
    assert isinstance(result, RateLimitResult)
    assert result.allowed is True
    assert result.limit == 10
    assert result.remaining >= 0
    assert result.reset_after > 0


@pytest.mark.asyncio
async def test_token_bucket_limiter_interface():
    """Verify TokenBucketLimiter returns standard RateLimitResult structure."""
    limiter = TokenBucketLimiter(capacity=5, refill_rate=1.0)
    result = await limiter.is_allowed("client-ip-test-2")
    assert isinstance(result, RateLimitResult)
    assert result.allowed is True
    assert result.limit == 5
    assert result.remaining >= 0
    assert result.reset_after >= 0
