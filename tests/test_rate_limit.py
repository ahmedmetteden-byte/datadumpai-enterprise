"""
Tests for core.rate_limit — the in-process sliding-window limiter now
protecting the OpenAI-calling report-generation and Ask/Intelligence
Studio endpoints from unbounded per-account request volume.
"""

from __future__ import annotations

import time

import pytest

from core.rate_limit import RateLimitExceeded, check_rate_limit, reset_all


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    reset_all()
    yield
    reset_all()


def test_allows_requests_up_to_the_limit():
    for _ in range(5):
        check_rate_limit("scope-a", "user-1", max_requests=5, window_seconds=60)


def test_raises_once_the_limit_is_exceeded():
    for _ in range(5):
        check_rate_limit("scope-a", "user-1", max_requests=5, window_seconds=60)

    with pytest.raises(RateLimitExceeded):
        check_rate_limit("scope-a", "user-1", max_requests=5, window_seconds=60)


def test_retry_after_is_a_positive_number_of_seconds():
    for _ in range(3):
        check_rate_limit("scope-a", "user-1", max_requests=3, window_seconds=60)

    with pytest.raises(RateLimitExceeded) as exc_info:
        check_rate_limit("scope-a", "user-1", max_requests=3, window_seconds=60)

    assert exc_info.value.retry_after_seconds > 0
    assert exc_info.value.retry_after_seconds <= 60


def test_different_users_have_independent_limits():
    for _ in range(3):
        check_rate_limit("scope-a", "user-1", max_requests=3, window_seconds=60)

    with pytest.raises(RateLimitExceeded):
        check_rate_limit("scope-a", "user-1", max_requests=3, window_seconds=60)

    # user-2 is untouched by user-1 having exhausted their allowance.
    check_rate_limit("scope-a", "user-2", max_requests=3, window_seconds=60)


def test_different_scopes_have_independent_limits_for_the_same_user():
    for _ in range(3):
        check_rate_limit("reports.generate", "user-1", max_requests=3, window_seconds=60)

    with pytest.raises(RateLimitExceeded):
        check_rate_limit("reports.generate", "user-1", max_requests=3, window_seconds=60)

    # A different scope for the same user (e.g. Ask vs. report generation)
    # is a separate bucket entirely.
    check_rate_limit("intelligence.ask", "user-1", max_requests=3, window_seconds=60)


def test_sliding_window_allows_requests_again_once_old_ones_age_out():
    for _ in range(2):
        check_rate_limit("scope-a", "user-1", max_requests=2, window_seconds=0.05)

    with pytest.raises(RateLimitExceeded):
        check_rate_limit("scope-a", "user-1", max_requests=2, window_seconds=0.05)

    time.sleep(0.1)

    # The two earlier timestamps are now outside the window, so this
    # succeeds instead of raising a third time.
    check_rate_limit("scope-a", "user-1", max_requests=2, window_seconds=0.05)
