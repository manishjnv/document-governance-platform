"""T-3028 / T-3029 acceptance tests: token-bucket rate limiter and circuit
breaker. Pure in-memory units, no DB — safe to run standalone."""

import asyncio

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.core.rate_limit import TokenBucket


def test_token_bucket_allows_then_rejects_then_refills():
    bucket = TokenBucket(capacity=3, rate=10.0)  # 10 tokens/sec refill

    for _ in range(3):
        allowed, _ = bucket.take()
        assert allowed is True

    allowed, retry_after = bucket.take()
    assert allowed is False
    assert retry_after > 0

    import time

    time.sleep(0.15)  # ~1.5 tokens refilled at 10/sec
    allowed, _ = bucket.take()
    assert allowed is True


async def test_circuit_breaker_opens_after_threshold_and_fails_fast():
    breaker = CircuitBreaker(failure_threshold=3, reset_timeout=0.2)

    async def always_fails():
        raise RuntimeError("boom")

    calls = 0

    async def counting_fail():
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(counting_fail)

    assert breaker.state == CircuitState.OPEN
    assert calls == 3

    # Breaker is open: call rejected without invoking the wrapped function.
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(counting_fail)
    assert calls == 3

    # After reset_timeout, breaker goes half-open and a success closes it.
    await asyncio.sleep(0.25)

    async def succeeds():
        return "ok"

    result = await breaker.call(succeeds)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED
