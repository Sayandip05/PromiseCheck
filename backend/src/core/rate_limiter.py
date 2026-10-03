"""Enterprise-grade rate limiting engine with Token Bucket and Sliding Window algorithms.

Supports:
1. Sliding Window (rolling log):
   - Prevents boundary burst anomalies by evaluating exact request timestamps within a sliding time delta.
   - Atomic evaluation via Redis Sorted Sets (ZSET).
2. Token Bucket:
   - Smooths traffic spikes with a configurable burst capacity and continuous refill rate.
   - Atomic evaluation via Redis Hash state and continuous refill calculation.
3. Resilient In-Memory Fallback:
   - Thread-safe local fallbacks if Redis is unreachable or during standalone testing.
4. FastAPI Dependency and Middleware Integration:
   - Emits RFC-compliant headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After.
"""

import asyncio
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request, Response, status

from core.logging import get_logger
from core.redis import get_async_redis

logger = get_logger("rate_limiter")


@dataclass
class RateLimitResult:
    """Represents the outcome of a rate limit evaluation."""

    allowed: bool
    limit: int
    remaining: int
    reset_after: int
    retry_after: int
    strategy: str


# ==============================================================================
# 1. Redis Lua Scripts (Atomic Execution)
# ==============================================================================

SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_req = tonumber(ARGV[3])
local member = ARGV[4]

-- 1. Remove elements outside the sliding window
local clear_before = now - window
redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)

-- 2. Count current elements in window
local current_reqs = redis.call('ZCARD', key)

if current_reqs < max_req then
    -- Allow: add current timestamp and refresh TTL
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, math.ceil(window) + 2)
    return {1, max_req - current_reqs - 1, math.ceil(window)}
else
    -- Reject: find oldest element to compute accurate retry_after
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if oldest and #oldest >= 2 then
        local oldest_time = tonumber(oldest[2])
        retry_after = math.max(1, math.ceil(oldest_time + window - now))
    end
    return {0, 0, retry_after}
end
"""

TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'tokens', 'last_updated')
local tokens = tonumber(data[1])
local last_updated = tonumber(data[2])

if tokens == nil then
    tokens = capacity
    last_updated = now
else
    local delta = math.max(0, now - last_updated)
    tokens = math.min(capacity, tokens + (delta * refill_rate))
    last_updated = now
end

if tokens >= cost then
    tokens = tokens - cost
    redis.call('HMSET', key, 'tokens', tokens, 'last_updated', last_updated)
    local ttl = math.max(60, math.ceil((capacity - tokens) / math.max(0.001, refill_rate)) + 30)
    redis.call('EXPIRE', key, ttl)
    local reset_after = math.ceil((capacity - tokens) / math.max(0.001, refill_rate))
    return {1, math.floor(tokens), reset_after}
else
    local needed = cost - tokens
    local retry_after = math.max(1, math.ceil(needed / math.max(0.001, refill_rate)))
    redis.call('HMSET', key, 'tokens', tokens, 'last_updated', last_updated)
    return {0, math.floor(tokens), retry_after}
end
"""


# ==============================================================================
# 2. In-Memory Resilient Fallbacks (Thread-Safe)
# ==============================================================================

class _InMemorySlidingWindowStore:
    def __init__(self) -> None:
        self._history: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def evaluate(self, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            timestamps = [t for t in self._history.get(key, []) if t > cutoff]

            if len(timestamps) < max_requests:
                timestamps.append(now)
                self._history[key] = timestamps
                return RateLimitResult(
                    allowed=True,
                    limit=max_requests,
                    remaining=max_requests - len(timestamps),
                    reset_after=window_seconds,
                    retry_after=0,
                    strategy="sliding_window_memory",
                )
            else:
                oldest = timestamps[0] if timestamps else now
                retry_after = max(1, math.ceil(oldest + window_seconds - now))
                self._history[key] = timestamps
                return RateLimitResult(
                    allowed=False,
                    limit=max_requests,
                    remaining=0,
                    reset_after=retry_after,
                    retry_after=retry_after,
                    strategy="sliding_window_memory",
                )


class _InMemoryTokenBucketStore:
    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_updated)
        self._lock = asyncio.Lock()

    async def evaluate(
        self, key: str, capacity: int, refill_rate: float, cost: int = 1
    ) -> RateLimitResult:
        async with self._lock:
            now = time.time()
            if key not in self._buckets:
                tokens = float(capacity)
                last_updated = now
            else:
                tokens, last_updated = self._buckets[key]
                delta = max(0.0, now - last_updated)
                tokens = min(float(capacity), tokens + (delta * refill_rate))
                last_updated = now

            if tokens >= cost:
                tokens -= cost
                self._buckets[key] = (tokens, last_updated)
                reset_after = math.ceil((capacity - tokens) / max(0.001, refill_rate))
                return RateLimitResult(
                    allowed=True,
                    limit=capacity,
                    remaining=int(tokens),
                    reset_after=reset_after,
                    retry_after=0,
                    strategy="token_bucket_memory",
                )
            else:
                needed = cost - tokens
                retry_after = max(1, math.ceil(needed / max(0.001, refill_rate)))
                self._buckets[key] = (tokens, last_updated)
                return RateLimitResult(
                    allowed=False,
                    limit=capacity,
                    remaining=int(tokens),
                    reset_after=retry_after,
                    retry_after=retry_after,
                    strategy="token_bucket_memory",
                )


_mem_sliding_window = _InMemorySlidingWindowStore()
_mem_token_bucket = _InMemoryTokenBucketStore()


# ==============================================================================
# 3. Strategy Implementations
# ==============================================================================

class SlidingWindowLimiter:
    """Sliding Window Log algorithm to prevent boundary spikes."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, identifier: str) -> RateLimitResult:
        key = f"ratelimit:sw:{identifier}"
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex[:8]}"

        try:
            r = get_async_redis()
            res = await r.eval(
                SLIDING_WINDOW_LUA,
                1,
                key,
                str(now),
                str(self.window_seconds),
                str(self.max_requests),
                member,
            )
            # res is [allowed, remaining, reset_or_retry]
            allowed = bool(res[0])
            remaining = int(res[1])
            reset_or_retry = int(res[2])

            return RateLimitResult(
                allowed=allowed,
                limit=self.max_requests,
                remaining=remaining,
                reset_after=reset_or_retry if allowed else reset_or_retry,
                retry_after=0 if allowed else reset_or_retry,
                strategy="sliding_window_redis",
            )
        except Exception as exc:
            logger.warning(f"Redis sliding window error, using in-memory fallback: {exc}")
            return await _mem_sliding_window.evaluate(key, self.max_requests, self.window_seconds)


class TokenBucketLimiter:
    """Token Bucket algorithm with configurable capacity and refill rate."""

    def __init__(self, capacity: int = 30, refill_rate: float = 1.0) -> None:
        """
        capacity: Maximum tokens the bucket can accumulate (burst capacity).
        refill_rate: Tokens added per second. (e.g. 1.0 = 60 tokens/min).
        """
        self.capacity = capacity
        self.refill_rate = refill_rate

    async def is_allowed(self, identifier: str, cost: int = 1) -> RateLimitResult:
        key = f"ratelimit:tb:{identifier}"
        now = time.time()

        try:
            r = get_async_redis()
            res = await r.eval(
                TOKEN_BUCKET_LUA,
                1,
                key,
                str(self.capacity),
                str(self.refill_rate),
                str(now),
                str(cost),
            )
            allowed = bool(res[0])
            remaining = int(res[1])
            reset_or_retry = int(res[2])

            return RateLimitResult(
                allowed=allowed,
                limit=self.capacity,
                remaining=remaining,
                reset_after=reset_or_retry,
                retry_after=0 if allowed else reset_or_retry,
                strategy="token_bucket_redis",
            )
        except Exception as exc:
            logger.warning(f"Redis token bucket error, using in-memory fallback: {exc}")
            return await _mem_token_bucket.evaluate(key, self.capacity, self.refill_rate, cost)


# ==============================================================================
# 4. Route-level Dependency Decorator
# ==============================================================================

def rate_limit(
    strategy: str = "sliding_window",
    max_requests: int = 60,
    window_seconds: int = 60,
    capacity: int = 30,
    refill_rate: float = 1.0,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """FastAPI route dependency for fine-grained rate limiting.

    Usage:
        @router.post("/items", dependencies=[Depends(rate_limit(strategy="token_bucket", capacity=10, refill_rate=0.5))])
    """
    if strategy == "token_bucket":
        limiter: Any = TokenBucketLimiter(capacity=capacity, refill_rate=refill_rate)
    else:
        limiter = SlidingWindowLimiter(max_requests=max_requests, window_seconds=window_seconds)

    async def dependency(request: Request, response: Response):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        custom_key = key_func(request) if key_func else f"{client_ip}:{path}"

        result: RateLimitResult = await limiter.is_allowed(custom_key)

        # Set standard RFC HTTP headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_after)

        if not result.allowed:
            response.headers["Retry-After"] = str(result.retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded ({result.strategy}). Retry in {result.retry_after}s.",
                    "retry_after": result.retry_after,
                },
                headers={"Retry-After": str(result.retry_after)},
            )

    return dependency
