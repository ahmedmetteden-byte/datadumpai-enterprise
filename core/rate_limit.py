"""
In-process, sliding-window rate limiting for authenticated, per-user
endpoints.

Generalizes the same pattern api/routers/public.py's contact-form
limiter already uses (a per-key timestamp log, pruned to a trailing
window) so cost-sensitive authenticated endpoints — the OpenAI-calling
report generation and Ask/Intelligence Studio endpoints, specifically —
can reuse it too, keyed by user id rather than IP.

In-memory and per-process, deliberately: this app runs as one API
instance (see SYSTEM_ARCHITECTURE.md's Docker layout — one `api`
service, not horizontally scaled), so a process-local counter enforces
a real, correct limit today. If this API is ever scaled to more than
one instance, each instance would enforce its own independent limit
rather than a shared one (a user could get roughly N times the intended
allowance by landing on N different instances) — move to a shared store
(Redis, or a dedicated Supabase-backed counter) at that point, not
before; this app has no such shared store today and none should be
added speculatively.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

# Keyed by (scope, key) so independent limits (e.g. "intelligence.ask" vs.
# "reports.generate") never share a bucket even for the same user.
_logs: dict[tuple[str, str], list[float]] = defaultdict(list)
_guard = Lock()


class RateLimitExceeded(Exception):
    """Raised when `key` has exceeded its allowance for `scope`."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Rate limit exceeded; retry after {retry_after_seconds}s"
        )


def check_rate_limit(
    scope: str,
    key: str,
    *,
    max_requests: int,
    window_seconds: int,
) -> None:
    """Record one request for (scope, key) and raise RateLimitExceeded if
    that pushes it over `max_requests` within the trailing
    `window_seconds`. A sliding window, not a fixed one: old timestamps
    are pruned on every call rather than the count resetting at a fixed
    boundary, so a burst can't game a reset edge.
    """

    now = time.monotonic()
    cutoff = now - window_seconds
    bucket = (scope, key)

    with _guard:
        recent = [ts for ts in _logs[bucket] if ts > cutoff]
        recent.append(now)
        _logs[bucket] = recent
        count = len(recent)
        oldest = recent[0]

    if count > max_requests:
        retry_after = max(1, int(oldest + window_seconds - now))
        raise RateLimitExceeded(retry_after)


def reset_all() -> None:
    """Test-only: clear every tracked bucket."""

    with _guard:
        _logs.clear()
