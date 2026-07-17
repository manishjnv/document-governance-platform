"""Circuit breaker for wrapping flaky async external calls (LLM APIs). T-3029.

ponytail: single-process in-memory state per breaker instance, no shared
state across replicas. Fine — a breaker is meant to protect *this process*
from hammering a downed dependency; cross-process coordination isn't the
point.
"""

import time
from enum import Enum
from functools import wraps
from typing import Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the breaker is open."""


class CircuitBreaker:
    """Closed -> Open after `failure_threshold` consecutive failures.
    Open -> Half-open once `reset_timeout` seconds have elapsed since the
    last failure; a half-open call that succeeds closes the breaker, one
    that fails re-opens it."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at: float = 0.0

    def _update_state(self) -> None:
        if self.state == CircuitState.OPEN and (time.monotonic() - self.opened_at) >= self.reset_timeout:
            self.state = CircuitState.HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs):
        self._update_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker open — failing fast (retry after "
                f"{max(0.0, self.reset_timeout - (time.monotonic() - self.opened_at)):.1f}s)"
            )

        try:
            result = await func(*args, **kwargs)
        except Exception:
            self.failure_count += 1
            if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
            raise
        else:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            return result

    def __call__(self, func: Callable) -> Callable:
        """Use as a decorator on an async function."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)

        return wrapper
