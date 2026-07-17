"""T-3005/T-3019: app.core.cache. No live Redis required -- see the
fail-open test, which is the acceptance-critical one (the whole suite must
still pass with no Redis server running)."""

import fakeredis.aioredis
import pytest

from app.core import cache as cache_module
from app.core.cache import cached, get_cached, invalidate_cache, set_cached


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    """Each test gets a clean module-level client singleton."""
    monkeypatch.setattr(cache_module, "_client", None)
    yield
    monkeypatch.setattr(cache_module, "_client", None)


@pytest.fixture
def fake_client(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(cache_module, "_get_client", lambda: client)
    return client


@pytest.mark.asyncio
async def test_set_get_roundtrip(fake_client):
    await set_cached("k1", {"a": 1}, ttl_seconds=60)
    assert await get_cached("k1") == {"a": 1}


@pytest.mark.asyncio
async def test_get_cached_miss(fake_client):
    assert await get_cached("does-not-exist") is None


@pytest.mark.asyncio
async def test_invalidate_cache_clears_matching_keys(fake_client):
    await set_cached("cache:foo:org1:aaa", {"v": 1}, ttl_seconds=60)
    await set_cached("cache:foo:org1:bbb", {"v": 2}, ttl_seconds=60)
    await set_cached("cache:foo:org2:ccc", {"v": 3}, ttl_seconds=60)

    await invalidate_cache("cache:*:org1:*")

    assert await get_cached("cache:foo:org1:aaa") is None
    assert await get_cached("cache:foo:org1:bbb") is None
    assert await get_cached("cache:foo:org2:ccc") == {"v": 3}


@pytest.mark.asyncio
async def test_redis_unreachable_falls_through_cleanly(monkeypatch):
    """Critical acceptance test: point at a host that can't be reached and
    confirm get/set/invalidate never raise, and @cached still calls the
    wrapped function instead of erroring the request."""
    monkeypatch.setattr(cache_module.settings, "redis_url", "redis://127.0.0.1:1/0")

    assert await get_cached("anything") is None
    await set_cached("anything", {"x": 1}, ttl_seconds=60)  # must not raise
    await invalidate_cache("cache:*")  # must not raise

    calls = {"n": 0}

    @cached(ttl_seconds=60)
    async def expensive(current_user=None, db=None):
        calls["n"] += 1
        return {"computed": True}

    result = await expensive()
    assert result == {"computed": True}
    assert calls["n"] == 1

    # a second call still falls through (Redis stays unreachable) but the
    # function keeps returning correct data rather than crashing
    result2 = await expensive()
    assert result2 == {"computed": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_cached_decorator_hits_cache(fake_client):
    calls = {"n": 0}

    @cached(ttl_seconds=60)
    async def expensive(current_user=None, db=None):
        calls["n"] += 1
        return {"computed": True}

    await expensive()
    await expensive()
    assert calls["n"] == 1  # second call served from cache
