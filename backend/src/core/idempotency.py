"""Enterprise idempotency and safe retry engine (IETF / Stripe standard).

Guarantees:
1. Safe Retries: If a client or proxy retries a mutating request with the same
   Idempotency-Key, the backend returns the cached response without re-executing
   business logic or inserting duplicate database rows.
2. Concurrency Control: Concurrent requests with the same key receive HTTP 409 Conflict
   with a Retry-After header while the initial request is in-flight.
3. Payload Fingerprinting: Detects if the same key is reused with a altered payload
   and rejects it with HTTP 422 Unprocessable Entity.
4. Tenant Isolation: Idempotency keys are strictly scoped by workspace ID and user ID
   to prevent cross-tenant collisions.
5. Storage: Redis backed with automatic TTL (24h) and thread-safe in-memory fallback.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse, Response as StarletteResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logging import get_logger
from core.metrics import metrics
from core.redis import get_async_redis

logger = get_logger("idempotency")

IDEMPOTENCY_HEADER = "idempotency-key"
ALT_IDEMPOTENCY_HEADER = "x-idempotency-key"
IDEMPOTENT_REPLAYED_HEADER = "idempotent-replayed"
DEFAULT_EXPIRY_SECONDS = 86400  # 24 hours
PROCESSING_LOCK_SECONDS = 30    # Max time an in-flight request can hold the lock


@dataclass
class CachedResponse:
    status_code: int
    headers: dict[str, str]
    body: str
    payload_hash: str
    created_at: float


class _InMemoryIdempotencyStore:
    """Thread-safe in-memory fallback for local development or when Redis is offline."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            entry = self._entries.get(key)
            if not entry:
                return None
            if entry.get("expires_at", 0) < time.time():
                del self._entries[key]
                return None
            return entry

    async def set_processing(self, key: str, payload_hash: str, ttl: int = PROCESSING_LOCK_SECONDS) -> bool:
        async with self._lock:
            now = time.time()
            existing = self._entries.get(key)
            if existing and existing.get("expires_at", 0) > now:
                return False  # Already exists (processing or completed)
            self._entries[key] = {
                "state": "PROCESSING",
                "payload_hash": payload_hash,
                "expires_at": now + ttl,
            }
            return True

    async def set_completed(
        self,
        key: str,
        payload_hash: str,
        status_code: int,
        headers: dict[str, str],
        body: str,
        ttl: int = DEFAULT_EXPIRY_SECONDS,
    ) -> None:
        async with self._lock:
            self._entries[key] = {
                "state": "COMPLETED",
                "payload_hash": payload_hash,
                "status_code": status_code,
                "headers": headers,
                "body": body,
                "expires_at": time.time() + ttl,
            }

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)


_memory_store = _InMemoryIdempotencyStore()


class IdempotencyManager:
    """Coordinates checking, locking, and persisting idempotent request outcomes."""

    @staticmethod
    def compute_payload_hash(body_bytes: bytes) -> str:
        """Generate SHA-256 fingerprint of the raw incoming request payload."""
        return hashlib.sha256(body_bytes).hexdigest()

    @staticmethod
    def build_idempotency_key(
        workspace_id: Optional[str],
        user_id: Optional[str],
        method: str,
        path: str,
        idempotency_key: str,
    ) -> str:
        """Construct a tenant-isolated storage key."""
        ws_part = workspace_id or "global"
        user_part = user_id or "anon"
        clean_key = idempotency_key.strip()[:256]
        return f"idempotency:{ws_part}:{user_part}:{method.upper()}:{path}:{clean_key}"

    @classmethod
    async def get_cached(cls, key: str) -> Optional[dict[str, Any]]:
        """Fetch cached idempotency record from Redis or memory."""
        try:
            r = get_async_redis()
            val = await r.get(key)
            if val:
                return json.loads(val)
        except Exception as exc:
            logger.warning(f"Redis idempotency fetch error, using memory fallback: {exc}")
            return await _memory_store.get(key)
        return None

    @classmethod
    async def acquire_processing_lock(
        cls, key: str, payload_hash: str, ttl: int = PROCESSING_LOCK_SECONDS
    ) -> bool:
        """Atomically claim execution lock for the incoming request."""
        try:
            r = get_async_redis()
            data = json.dumps({
                "state": "PROCESSING",
                "payload_hash": payload_hash,
                "created_at": time.time(),
            })
            # SET key value NX EX ttl ensures strictly one concurrent caller proceeds
            acquired = await r.set(key, data, nx=True, ex=ttl)
            return bool(acquired)
        except Exception as exc:
            logger.warning(f"Redis idempotency lock error, using memory fallback: {exc}")
            return await _memory_store.set_processing(key, payload_hash, ttl)

    @classmethod
    async def save_completed_response(
        cls,
        key: str,
        payload_hash: str,
        status_code: int,
        headers: dict[str, str],
        body: str,
        ttl: int = DEFAULT_EXPIRY_SECONDS,
    ) -> None:
        """Store the successful response for subsequent idempotent replay."""
        # Sanitize headers to avoid storing hop-by-hop or content-length conflicts
        cached_headers = {
            k.lower(): v
            for k, v in headers.items()
            if k.lower() not in ("content-length", "transfer-encoding", "connection", "date")
        }
        data = {
            "state": "COMPLETED",
            "payload_hash": payload_hash,
            "status_code": status_code,
            "headers": cached_headers,
            "body": body,
            "created_at": time.time(),
        }
        try:
            r = get_async_redis()
            await r.set(key, json.dumps(data), ex=ttl)
        except Exception as exc:
            logger.warning(f"Redis idempotency save error, using memory fallback: {exc}")
            await _memory_store.set_completed(key, payload_hash, status_code, cached_headers, body, ttl)

    @classmethod
    async def release_lock(cls, key: str) -> None:
        """Clear processing lock if request fails, permitting safe retry."""
        try:
            r = get_async_redis()
            await r.delete(key)
        except Exception as exc:
            logger.warning(f"Redis idempotency lock release error: {exc}")
            await _memory_store.delete(key)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Intercepts mutating HTTP requests (POST, PUT, PATCH) when an Idempotency-Key is provided.

    Behavior:
    - If key is new: acquires distributed lock, proceeds to handler, and caches 2xx response.
    - If request is in-flight: returns HTTP 409 Conflict with Retry-After header.
    - If request previously succeeded: returns identical cached response with Idempotent-Replayed: true.
    - If request payload differed: returns HTTP 422 Unprocessable Entity.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Idempotency applies to mutating operations only
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Look up Idempotency-Key header (case-insensitive)
        raw_key = request.headers.get(IDEMPOTENCY_HEADER) or request.headers.get(ALT_IDEMPOTENCY_HEADER)
        if not raw_key:
            return await call_next(request)

        # Read and cache request body so downstream handlers and Pydantic can still consume it
        body_bytes = await request.body()
        async def receive_cached():
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        request = Request(request.scope, receive=receive_cached)

        payload_hash = IdempotencyManager.compute_payload_hash(body_bytes)

        # Extract workspace and user context if available from headers or cookies
        workspace_id = request.headers.get("x-workspace-id")
        user_id = request.headers.get("x-user-id")
        storage_key = IdempotencyManager.build_idempotency_key(
            workspace_id=workspace_id,
            user_id=user_id,
            method=request.method,
            path=request.url.path,
            idempotency_key=raw_key,
        )

        # Check existing record
        cached = await IdempotencyManager.get_cached(storage_key)
        if cached:
            state = cached.get("state")
            cached_hash = cached.get("payload_hash", "")

            # Verify payload fingerprint
            if cached_hash != payload_hash:
                logger.warning(
                    f"Idempotency conflict for key '{raw_key}': payload hash mismatch."
                )
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "error": "Idempotency Conflict",
                        "message": "Idempotency key was previously used with a different request payload.",
                    },
                )

            # Check if previous execution is still processing
            if state == "PROCESSING":
                logger.info(f"Concurrent in-flight duplicate request for key '{raw_key}'")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "error": "Conflict",
                        "message": "A request with this idempotency key is currently in progress. Please retry in a moment.",
                        "retry_after": 2,
                    },
                    headers={"Retry-After": "2"},
                )

            # Replay completed response
            if state == "COMPLETED":
                metrics.record_idempotent_replay(request.url.path)
                logger.info(f"[idempotency] Replaying cached response for idempotency key '{raw_key}' on {request.url.path}")
                resp_headers = dict(cached.get("headers", {}))
                resp_headers[IDEMPOTENT_REPLAYED_HEADER] = "true"
                resp_headers[IDEMPOTENCY_HEADER] = raw_key
                return StarletteResponse(
                    content=cached.get("body", ""),
                    status_code=cached.get("status_code", 200),
                    headers=resp_headers,
                    media_type="application/json",
                )

        # Claim the lock
        acquired = await IdempotencyManager.acquire_processing_lock(storage_key, payload_hash)
        if not acquired:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "Conflict",
                    "message": "A request with this idempotency key is currently in progress. Please retry in a moment.",
                    "retry_after": 2,
                },
                headers={"Retry-After": "2"},
            )

        try:
            response = await call_next(request)

            # Only cache successful 2xx mutating responses
            if 200 <= response.status_code < 300:
                # Read response body iterator
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
                full_body = b"".join(body_chunks)
                body_str = full_body.decode("utf-8", errors="replace")

                await IdempotencyManager.save_completed_response(
                    key=storage_key,
                    payload_hash=payload_hash,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=body_str,
                )

                response_headers = dict(response.headers)
                response_headers[IDEMPOTENCY_HEADER] = raw_key

                return StarletteResponse(
                    content=full_body,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.media_type,
                )
            else:
                # On client (4xx) or server (5xx) error, release lock so client can fix & retry
                await IdempotencyManager.release_lock(storage_key)
                return response

        except Exception as exc:
            # On unexpected error, release lock so subsequent retry can proceed
            await IdempotencyManager.release_lock(storage_key)
            raise exc
