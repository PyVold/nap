# ============================================================================
# shared/rate_limiter.py - Rate limiting middleware for API protection
# ============================================================================

import time
from typing import Dict, Optional, Callable
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import asyncio
import os

from shared.logger import setup_logger

logger = setup_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production with multiple instances, replace with Redis-based implementation.
    """

    def __init__(self):
        # {key: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (IP, user_id, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            (is_allowed, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()
            window_start = now - window_seconds

            # Clean old entries
            self._requests[key] = [
                (ts, count) for ts, count in self._requests[key]
                if ts > window_start
            ]

            # Count requests in window
            total_requests = sum(count for _, count in self._requests[key])

            if total_requests >= max_requests:
                # Calculate retry-after
                if self._requests[key]:
                    oldest_ts = min(ts for ts, _ in self._requests[key])
                    retry_after = int(oldest_ts + window_seconds - now) + 1
                else:
                    retry_after = window_seconds
                return False, max(1, retry_after)

            # Add new request
            self._requests[key].append((now, 1))
            return True, 0

    async def cleanup(self, max_age_seconds: int = 3600):
        """Remove stale entries older than max_age_seconds"""
        async with self._lock:
            now = time.time()
            cutoff = now - max_age_seconds

            keys_to_remove = []
            for key, entries in self._requests.items():
                self._requests[key] = [
                    (ts, count) for ts, count in entries
                    if ts > cutoff
                ]
                if not self._requests[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._requests[key]


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting requests.

    Configuration via environment variables:
    - RATE_LIMIT_ENABLED: Enable/disable rate limiting (default: true)
    - RATE_LIMIT_REQUESTS: Max requests per window (default: 100)
    - RATE_LIMIT_WINDOW: Window size in seconds (default: 60)
    - RATE_LIMIT_BY: What to rate limit by: "ip", "user", "both" (default: "ip")
    """

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.max_requests = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
        self.window_seconds = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))
        self.limit_by = os.environ.get("RATE_LIMIT_BY", "ip")

        # Endpoints to exclude from rate limiting
        self.excluded_paths = {
            "/health",
            "/metrics",
            "/ready",
            "/live",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

        logger.info(
            f"Rate limiter initialized: {self.max_requests} requests/{self.window_seconds}s "
            f"(enabled={self.enabled}, by={self.limit_by})"
        )

    def _get_client_key(self, request: Request) -> str:
        """Extract rate limit key from request"""
        keys = []

        if self.limit_by in ("ip", "both"):
            # Get client IP (handle proxies)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
            keys.append(f"ip:{client_ip}")

        if self.limit_by in ("user", "both"):
            # Get user from auth header if present
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # Use token hash as user identifier
                import hashlib
                token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
                keys.append(f"user:{token_hash}")

        return ":".join(keys) if keys else "anonymous"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""

        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Check rate limit
        client_key = self._get_client_key(request)
        is_allowed, retry_after = await _rate_limiter.is_allowed(
            client_key,
            self.max_requests,
            self.window_seconds
        )

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {client_key}")
            raise RateLimitExceeded(retry_after)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)

        return response


# Cleanup task for removing stale entries
async def rate_limiter_cleanup_task():
    """Background task to clean up stale rate limit entries"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        await _rate_limiter.cleanup()


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter
