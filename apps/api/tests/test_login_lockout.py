"""Unit tests for app/core/login_lockout.py -- the in-memory failed-login
tracker wired into POST /login (app/routers/auth.py).

Complements the HTTP-level lockout tests in tests/test_auth.py::TestLogin
with tests of the module's internal bookkeeping (eviction cap) that don't
need a live login flow.
"""

from app.core import login_lockout


def _reset():
    login_lockout._failures.clear()
    login_lockout._locked_until.clear()


def test_lockout_triggers_at_max_attempts():
    _reset()
    for _ in range(login_lockout.MAX_FAILED_ATTEMPTS - 1):
        login_lockout.record_failure("victim@example.com")
    locked, _ = login_lockout.is_locked("victim@example.com")
    assert locked is False

    login_lockout.record_failure("victim@example.com")
    locked, remaining = login_lockout.is_locked("victim@example.com")
    assert locked is True
    assert remaining > 0
    _reset()


def test_success_clears_failure_state():
    _reset()
    login_lockout.record_failure("someone@example.com")
    login_lockout.record_failure("someone@example.com")
    login_lockout.record_success("someone@example.com")
    assert "someone@example.com" not in login_lockout._failures
    _reset()


def test_email_matching_is_case_and_whitespace_insensitive():
    _reset()
    for _ in range(login_lockout.MAX_FAILED_ATTEMPTS):
        login_lockout.record_failure("  Victim@Example.com  ")
    locked, _ = login_lockout.is_locked("victim@example.com")
    assert locked is True
    _reset()


def test_tracked_email_count_is_capped():
    """Regression for the unbounded-memory-growth finding from the
    2026-07-17 adversarial review: an attacker submitting one failed
    attempt each for many distinct fabricated emails must not grow
    _failures without bound."""
    _reset()
    original_cap = login_lockout.MAX_TRACKED_EMAILS
    login_lockout.MAX_TRACKED_EMAILS = 50
    try:
        for i in range(200):
            login_lockout.record_failure(f"attacker-{i}@example.com")
        assert len(login_lockout._failures) <= login_lockout.MAX_TRACKED_EMAILS
    finally:
        login_lockout.MAX_TRACKED_EMAILS = original_cap
        _reset()
