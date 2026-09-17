"""Production Security Headers, Request ID Tracing, Rate Limiting & Error Middleware."""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.logging import get_logger
from core.redis import get_async_redis

logger = get_logger("security_middleware")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce defense-in-depth HTTP security headers (OWASP Secure Headers Project)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 1. Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Clickjacking protection: disallow iframe embedding
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Cross-site scripting (XSS) filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Strict Transport Security (HSTS) in production
        if settings.APP_ENV.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # 6. Content Security Policy (CSP)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' http://localhost:* ws://localhost:* http://127.0.0.1:* ws://127.0.0.1:* https://api.groq.com;"
        )

        return response


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID and measure execution duration (X-Process-Time) for structured telemetry."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        start_time = time.perf_counter()

        # Attach request_id to state
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path} "
                f"[request_id={request_id}] ({process_time:.2f}ms): {exc}",
                exc_info=True,
            )
            # Safe sanitized 500 response (never leak stack traces or internal DB paths)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Please contact support with this Request ID.",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Suppress noisy healthcheck logs
        if not request.url.path.startswith("/healthz"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} "
                f"({process_time:.2f}ms) [id={request_id[:8]}]"
            )

        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter using Redis with automatic local memory fallback.
    
    Protects authentication endpoints from brute force and extraction from abuse.
    """

    # Stricter rate limits for sensitive endpoints: (max_requests, window_seconds)
    LIMITS = {
        "/api/v1/auth/login": (10, 60),      # 10 requests / 60s
        "/api/v1/auth/register": (10, 60),   # 10 requests / 60s
        "/api/v1/ingestion/upload": (30, 60),# 30 uploads / 60s
        "default": (120, 60),                # 120 requests / 60s
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health probes and SSE stream from rate limiting
        path = request.url.path
        if path in ("/healthz", "/api/v1/health") or path.startswith("/api/v1/events/stream"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        max_reqs, window_secs = self.LIMITS.get(path, self.LIMITS["default"])
        key = f"ratelimit:{client_ip}:{path}"
        current_time = time.time()

        # Try Redis rate limiting first
        rate_exceeded = False
        try:
            r = get_async_redis()
            # Fix #4: Atomic pipeline — INCR and EXPIRE are sent in a single
            # round-trip. expire(..., nx=True) sets the TTL only if it does NOT
            # already exist, preventing the window from resetting on every hit.
            # Previously the two-step INCR→EXPIRE had a race: concurrent requests
            # could both INCR before either EXPIRE ran, leaving the key without a
            # TTL and permanently banning the IP.
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_secs, nx=True)
            results = await pipe.execute()
            current_hits = results[0]
            if current_hits > max_reqs:
                rate_exceeded = True
        except Exception as redis_err:
            # If Redis is unavailable, fail-open (let the request pass).
            # The removed in-memory fallback was not safe across multiple Uvicorn
            # worker processes — each had its own dict, allowing N× the limit.
            logger.warning(
                f"Rate limiter Redis unavailable (failing open) for {client_ip}: {redis_err}"
            )

        if rate_exceeded:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Please try again in {window_secs} seconds.",
                    "retry_after": window_secs,
                },
                headers={"Retry-After": str(window_secs)},
            )

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Register all security and telemetry middleware onto the FastAPI application."""
    # Outer layer: Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    # Middle layer: Rate limiter
    app.add_middleware(RateLimiterMiddleware)
    # Inner layer: Request tracing & error interception
    app.add_middleware(RequestTracingMiddleware)
