"""Production Security Headers, Request ID Tracing, Rate Limiting & Error Middleware."""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import settings
from core.logging import get_logger
from core.metrics import metrics
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
        # SECURITY: 'unsafe-inline' is forbidden in production because it allows
        # XSS payload execution via injected inline scripts.
        # This is a pure API server — no HTML pages are served in production so
        # no inline scripts or styles are ever needed.
        # In development mode we relax for Swagger UI (/docs) which uses inline JS.
        if settings.APP_ENV.lower() == "production":
            csp = (
                "default-src 'none'; "
                "connect-src 'self'; "
                "img-src 'self' data: https:; "
                "frame-ancestors 'none';"
            )
        else:
            # Development: allow inline for Swagger UI
            csp = (
                "default-src 'self'; "
                "img-src 'self' data: https:; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' http://localhost:* ws://localhost:* "
                "http://127.0.0.1:* ws://127.0.0.1:* https://api.groq.com;"
            )
        response.headers["Content-Security-Policy"] = csp

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

        duration_sec = time.perf_counter() - start_time
        process_time = duration_sec * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Record HTTP telemetry in Prometheus metrics collector
        metrics.record_request(request.method, request.url.path, response.status_code, duration_sec)

        # Performance Alert: flag slow requests exceeding 500ms threshold
        if process_time > 500 and not request.url.path.startswith("/api/v1/events/stream"):
            logger.warning(
                f"[perf] Slow request: {request.method} {request.url.path} took {process_time:.2f}ms [id={request_id[:8]}]"
            )

        # Suppress noisy healthcheck logs
        if not request.url.path.startswith("/healthz"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} "
                f"({process_time:.2f}ms) [id={request_id[:8]}]"
            )

        return response


from core.rate_limiter import SlidingWindowLimiter, TokenBucketLimiter, RateLimitResult


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Dual-algorithm enterprise rate limiter.
    
    - Sliding Window: Protects auth and high-frequency endpoints from boundary burst anomalies.
    - Token Bucket: Smooths bursty traffic for compute-intensive file ingestion.
    - Adds standard RFC headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        # Dedicated algorithm instances
        self.auth_login_limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        self.auth_register_limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        self.upload_limiter = TokenBucketLimiter(capacity=10, refill_rate=0.5)  # 30/min sustained
        self.default_limiter = SlidingWindowLimiter(max_requests=120, window_seconds=60)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        # Bypass rate limiting for internal health probes and real-time SSE stream
        if path in ("/healthz", "/api/v1/health") or path.startswith("/api/v1/events/stream"):
            return await call_next(request)

        client_ip = (
            request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else "unknown")
        )
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        identifier = f"{client_ip}:{path}"

        # Route to appropriate algorithm
        if path == "/api/v1/auth/login":
            result: RateLimitResult = await self.auth_login_limiter.is_allowed(identifier)
        elif path == "/api/v1/auth/register":
            result = await self.auth_register_limiter.is_allowed(identifier)
        elif path.startswith("/api/v1/ingestion"):
            result = await self.upload_limiter.is_allowed(identifier)
        else:
            result = await self.default_limiter.is_allowed(identifier)

        if not result.allowed:
            metrics.record_rate_limit(path)
            logger.warning(
                f"Rate limit exceeded ({result.strategy}) for IP {client_ip} on {path}. Retry after {result.retry_after}s"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Please try again in {result.retry_after} seconds.",
                    "retry_after": result.retry_after,
                },
                headers={
                    "Retry-After": str(result.retry_after),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_after),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_after)
        return response


from core.idempotency import IdempotencyMiddleware


def register_middleware(app: FastAPI) -> None:
    """Register all security, telemetry, and idempotency middleware onto the FastAPI application."""
    # Outer layer: Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    # Middle layer: Rate limiter
    app.add_middleware(RateLimiterMiddleware)
    # Idempotency layer: Safe retries & duplicate prevention
    app.add_middleware(IdempotencyMiddleware)
    # Inner layer: Request tracing & error interception
    app.add_middleware(RequestTracingMiddleware)
