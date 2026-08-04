"""In-memory token-bucket rate limiting middleware. T-3028.

ponytail: single-process in-memory bucket dict, no Redis/distributed state.
Fine for one API instance; move to Redis (INCR + TTL or a Lua token-bucket
script) if the app ever runs multiple replicas behind a load balancer.
"""

import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth import verify_token
from app.config import settings

EXEMPT_PATHS = {"/health"}

# Caps unbounded growth of the per-key bucket dict -- an unauthenticated
# caller rotating IPs (or a scanner hitting many distinct paths/hosts) would
# otherwise create one TokenBucket entry per unique key forever, with no
# eviction, for the lifetime of the process (memory-exhaustion DoS; same
# class of bug fixed in app/core/login_lockout.py's MAX_TRACKED_EMAILS).
# Plain dicts preserve insertion order in Python 3.7+, so evicting the
# oldest-inserted entry is an O(1) `next(iter(...))` -- no LRU structure
# needed.
MAX_TRACKED_KEYS = 10_000


class TokenBucket:
    """Classic token bucket: refills continuously at `rate` tokens/sec, caps
    at `capacity`. `take()` returns (allowed, seconds_until_next_token)."""

    def __init__(self, capacity: float, rate: float):
        self.capacity = capacity
        self.rate = rate
        self.tokens = capacity
        self.updated_at = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated_at = now

    def take(self, cost: float = 1.0) -> tuple[bool, float]:
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True, 0.0
        deficit = cost - self.tokens
        return False, deficit / self.rate


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter keyed by authenticated user id (from the
    Bearer token) else client IP. Exempts EXEMPT_PATHS (health checks)."""

    def __init__(self, app, requests_per_minute: Optional[int] = None, burst: Optional[int] = None):
        super().__init__(app)
        self.rate_per_minute = requests_per_minute or settings.rate_limit_requests_per_minute
        self.rate_per_sec = self.rate_per_minute / 60.0
        self.capacity = burst or self.rate_per_minute
        self.buckets: dict[str, TokenBucket] = {}

    def _key_for(self, request) -> str:
        auth_header = request.headers.get("authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token_data = verify_token(parts[1], token_type="access")
                if token_data:
                    return f"user:{token_data.user_id}"
        client = request.client
        return f"ip:{client.host if client else 'unknown'}"

    async def dispatch(self, request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        key = self._key_for(request)
        bucket = self.buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(self.capacity, self.rate_per_sec)
            self.buckets[key] = bucket
            if len(self.buckets) > MAX_TRACKED_KEYS:
                self.buckets.pop(next(iter(self.buckets)))

        allowed, retry_after = bucket.take()
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(max(1, int(retry_after) + 1))},
            )

        return await call_next(request)
