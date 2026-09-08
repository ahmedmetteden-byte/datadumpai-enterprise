"""
Backend error monitoring (Sentry).

Mirrors the adapter pattern already established in marketing-site/src/
lib/monitoring/ (MonitoringAdapter -> noop / concrete adapter, module-
level init + capture functions) so both surfaces follow the same shape
even though they're different languages/frameworks. Unlike that site's
sentry-adapter.ts (currently a stub — @sentry/nextjs was never
installed there), this one is real: sentry-sdk is a normal PyPI package
with a first-class FastAPI/Starlette integration, so there's no reason
to leave it unfinished here too.

Before this module, apps/api and apps/webhooks had zero error tracking
— an unhandled exception's only trace was a local stdout log line
(uvicorn's default handling), invisible once a deploy rotates logs or
the container restarts. The marketing site's Sentry wiring (even once
someone finishes the stub) doesn't cover either of these processes.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import config

logger = logging.getLogger(__name__)


class MonitoringAdapter(Protocol):
    def capture_exception(
        self, error: BaseException, **context: Any
    ) -> None: ...

    def capture_message(self, message: str, *, level: str = "info") -> None: ...


class _NoopAdapter:
    """Default adapter — monitoring disabled (no SENTRY_DSN configured)."""

    def capture_exception(self, error: BaseException, **context: Any) -> None:
        pass

    def capture_message(self, message: str, *, level: str = "info") -> None:
        pass


class _SentryAdapter:
    """Backed by a real, already-initialized sentry_sdk client."""

    def capture_exception(self, error: BaseException, **context: Any) -> None:
        import sentry_sdk

        if context:
            with sentry_sdk.new_scope() as scope:
                for key, value in context.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_exception(error)
        else:
            sentry_sdk.capture_exception(error)

    def capture_message(self, message: str, *, level: str = "info") -> None:
        import sentry_sdk

        sentry_sdk.capture_message(message, level=level)


_adapter: MonitoringAdapter = _NoopAdapter()
_initialized = False


def is_monitoring_enabled() -> bool:
    """True once init_monitoring() has wired a real (non-noop) adapter."""

    return isinstance(_adapter, _SentryAdapter)


def init_monitoring(*, service_name: str) -> None:
    """Initialize backend error monitoring. Safe to call multiple times
    (e.g. once per worker/reload) — re-initializing sentry_sdk with the
    same config is a no-op on Sentry's side.

    `service_name` tags events so the API and webhooks processes (which
    share this module but run as separate services — see
    docker-compose.yml) are distinguishable in Sentry, since both would
    otherwise report under one indistinguishable project.
    """

    global _adapter, _initialized

    if not config.is_sentry_configured():
        _adapter = _NoopAdapter()
        _initialized = True
        return

    import sentry_sdk
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.ENVIRONMENT,
        release=config.APP_VERSION,
        traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # Unhandled exceptions are already captured automatically by the
        # Starlette/FastAPI integrations above via the ASGI middleware —
        # this adapter's capture_exception() is for explicit reporting of
        # exceptions the app already caught and would otherwise only log.
    )
    sentry_sdk.set_tag("service", service_name)
    _adapter = _SentryAdapter()
    _initialized = True
    logger.info("Sentry monitoring initialized for service=%s", service_name)


def capture_exception(error: BaseException, **context: Any) -> None:
    """Explicitly report a caught exception. Use for a failure that's
    already handled (logged, and execution continues) but still worth
    knowing about — not needed for exceptions that propagate out of a
    request handler, which the FastAPI/Starlette integration reports on
    its own."""

    _adapter.capture_exception(error, **context)


def capture_message(message: str, *, level: str = "info") -> None:
    _adapter.capture_message(message, level=level)


def reset_for_tests() -> None:
    """Test-only: restore the no-op adapter and uninitialized state, and
    tear down sentry_sdk's own *global* client if a prior test's
    init_monitoring() call created one — sentry_sdk.init() sets
    process-wide state that this module's own _adapter/_initialized
    reset alone doesn't touch. Left unclosed, a real (if fake-DSN)
    client's background worker outlives the test and tries to flush
    queued events — with a real network timeout — at interpreter exit.
    close(timeout=0) shuts it down immediately instead of waiting.
    """

    global _adapter, _initialized

    _adapter = _NoopAdapter()
    _initialized = False

    import sentry_sdk

    client = sentry_sdk.get_client()
    if client.is_active():
        client.close(timeout=0)
    sentry_sdk.get_global_scope().set_client(None)
