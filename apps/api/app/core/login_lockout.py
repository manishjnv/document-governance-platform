"""In-memory login-failure lockout: 5 failed attempts -> 15 minute lockout,
keyed by normalized email.

ponytail: single-process in-memory dict, same pattern/limitation as
app/core/rate_limit.py's TokenBucket (documented there) -- fine for one API
instance, move to Redis (INCR + TTL) if the app ever runs multiple replicas.

This existed only as dead config (Settings.rate_limit_login_attempts) and an
unused `429` response documented on the /login route -- no code actually
tracked failures or enforced a lockout.
"""

import time

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60

# Caps unbounded growth from an unauthenticated caller submitting failed
# logins for thousands of distinct fabricated emails (a pre-auth memory-
# exhaustion DoS this module had with no cap at all). Plain dicts preserve
# insertion order in Python 3.7+, so evicting the oldest-inserted entry is
# an O(1) `next(iter(...))` -- no separate LRU structure needed.
MAX_TRACKED_EMAILS = 10_000

_failures: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}


def _key(email: str) -> str:
    return email.strip().lower()


def _evict_oldest_if_over_capacity() -> None:
    while len(_failures) > MAX_TRACKED_EMAILS:
        _failures.pop(next(iter(_failures)))
    while len(_locked_until) > MAX_TRACKED_EMAILS:
        _locked_until.pop(next(iter(_locked_until)))


def is_locked(email: str) -> tuple[bool, float]:
    """Returns (locked, seconds_remaining)."""
    key = _key(email)
    until = _locked_until.get(key)
    if until is None:
        return False, 0.0

    remaining = until - time.monotonic()
    if remaining <= 0:
        _locked_until.pop(key, None)
        _failures.pop(key, None)
        return False, 0.0

    return True, remaining


def record_failure(email: str) -> None:
    key = _key(email)
    now = time.monotonic()
    attempts = _failures.setdefault(key, [])
    attempts.append(now)

    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        _locked_until[key] = now + LOCKOUT_SECONDS
        _failures.pop(key, None)

    _evict_oldest_if_over_capacity()


def record_success(email: str) -> None:
    key = _key(email)
    _failures.pop(key, None)
    _locked_until.pop(key, None)
