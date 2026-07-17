"""Redis-backed response cache. T-3005/T-3019.

Fails open by design: any Redis error (unreachable host, timeout, bad
response) is caught, logged, and treated as a cache miss so a request never
errors just because Redis is down. Tests run with no Redis server available
and rely on this behavior.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        # decode_responses so get() returns str, not bytes
        _client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    return _client


async def get_cached(key: str) -> Any:
    """Returns the cached value, or None on a miss or any Redis failure."""
    try:
        raw = await _get_client().get(key)
    except Exception as exc:
        logger.warning("cache get failed for key=%s: %s", key, exc)
        return None
    return json.loads(raw) if raw is not None else None


async def set_cached(key: str, value: Any, ttl_seconds: int) -> None:
    """Best-effort cache write; swallows Redis errors."""
    try:
        await _get_client().set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as exc:
        logger.warning("cache set failed for key=%s: %s", key, exc)


async def invalidate_cache(pattern: str) -> None:
    """Delete every key matching a SCAN glob pattern (e.g. 'cache:*:<org_id>:*')."""
    try:
        client = _get_client()
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
    except Exception as exc:
        logger.warning("cache invalidate failed for pattern=%s: %s", pattern, exc)


def _cache_key(func: Callable, kwargs: dict) -> str:
    """cache:<func>:<org_id>:<hash-of-remaining-kwargs>.

    org_id is pulled out and kept plain (not hashed) so invalidate_cache can
    target "every cached response for this org" with a prefix pattern.
    `db`/`response` (FastAPI-injected session/response objects) aren't
    serializable and don't affect the result, so they're excluded.
    """
    org_id = "global"
    current_user = kwargs.get("current_user")
    if current_user is not None and hasattr(current_user, "org_id"):
        org_id = str(current_user.org_id)

    parts = []
    for name, value in sorted(kwargs.items()):
        if name in ("db", "response", "current_user"):
            continue
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        parts.append(f"{name}={value}")
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
    return f"cache:{func.__module__}.{func.__name__}:{org_id}:{digest}"


def cached(ttl_seconds: int):
    """Decorator for async FastAPI endpoint functions: caches the JSON-
    serializable return value in Redis, keyed by function identity + org_id +
    remaining kwargs. Cache-miss (including any Redis failure) just calls the
    wrapped function directly.

    T-3016: if the wrapped endpoint declares a `response: Response` kwarg,
    Cache-Control and ETag (hash of the payload) are stamped on it on both
    hit and miss -- set here, not in the endpoint body, so a cache hit (which
    skips the endpoint body entirely) still gets the headers.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = _cache_key(func, kwargs)
            hit = await get_cached(key)
            if hit is not None:
                result = hit
            else:
                result = await func(*args, **kwargs)
                await set_cached(key, result, ttl_seconds)

            response = kwargs.get("response")
            if response is not None:
                etag = hashlib.sha256(
                    json.dumps(result, default=str, sort_keys=True).encode()
                ).hexdigest()[:16]
                response.headers["Cache-Control"] = f"public, max-age={ttl_seconds}"
                response.headers["ETag"] = f'"{etag}"'
            return result

        return wrapper

    return decorator
