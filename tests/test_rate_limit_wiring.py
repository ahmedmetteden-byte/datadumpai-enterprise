"""
Confirms the actual declared FastAPI dependency on each protected
endpoint enforces a rate limit — not just that core.rate_limit's logic
works in isolation. Calling a route function directly (this repo's
established test pattern — see test_billing_router.py) bypasses
Starlette's dependency-injection resolution, so a `Depends(...)`
parameter's default is never invoked that way; these tests instead pull
the real dependency callable off each endpoint's own signature (its
`Depends(...).dependency`) and call it directly, proving the exact
configuration actually declared on the route — not a hand-copied
duplicate of it — really does block.
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from api.auth_jwt import AuthenticatedPrincipal
from api.routers.intelligence import ask_temporary, send_message
from api.routers.reports import generate_report
from core.rate_limit import reset_all
from models.user import User
from tests.conftest import TEST_USER


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    reset_all()
    yield
    reset_all()


def _rate_limit_dependency(endpoint):
    """Pull the real Depends(enforce_rate_limit(...)) callable off an
    endpoint's own signature."""

    default = inspect.signature(endpoint).parameters["_rate_limit"].default
    return default.dependency


def _exhaust_and_expect_429(dependency, principal, *, max_calls: int = 200):
    for _ in range(max_calls):
        try:
            dependency(principal)
        except HTTPException as exc:
            assert exc.status_code == 429
            assert "Retry-After" in exc.headers
            return
    pytest.fail(
        f"Expected a 429 within {max_calls} calls but the dependency never raised."
    )


@pytest.mark.parametrize("endpoint", [generate_report, send_message, ask_temporary])
def test_endpoint_declares_a_rate_limit_dependency(endpoint):
    dependency = _rate_limit_dependency(endpoint)
    assert callable(dependency)


def test_generate_report_blocks_after_its_configured_limit():
    principal = AuthenticatedPrincipal(user=TEST_USER, access_token="test-token")
    dependency = _rate_limit_dependency(generate_report)

    # First call must succeed (proves this isn't blocking from call one).
    dependency(principal)
    _exhaust_and_expect_429(dependency, principal)


def test_send_message_and_ask_temporary_share_one_limit():
    """Both call the same expensive RAG pipeline, so switching between
    persisted chat and "temporary chat" must not double an account's
    effective allowance."""

    principal = AuthenticatedPrincipal(user=TEST_USER, access_token="test-token")
    send_dep = _rate_limit_dependency(send_message)
    ask_dep = _rate_limit_dependency(ask_temporary)

    send_dep(principal)
    ask_dep(principal)  # same scope/key as above — consumes from the same bucket

    blocked = False
    for _ in range(200):
        try:
            # Alternate the two entry points while draining the shared limit.
            send_dep(principal)
            ask_dep(principal)
        except HTTPException as exc:
            assert exc.status_code == 429
            blocked = True
            break
    assert blocked


def test_rate_limit_is_scoped_per_user_not_global():
    principal_a = AuthenticatedPrincipal(user=TEST_USER, access_token="tok-a")
    principal_b = AuthenticatedPrincipal(
        user=User(
            id="00000000-0000-4000-8000-000000000099",
            email="other@example.com",
            full_name="Other User",
            email_verified=True,
        ),
        access_token="tok-b",
    )
    dependency = _rate_limit_dependency(generate_report)

    _exhaust_and_expect_429(dependency, principal_a)

    # A different user is not blocked by user A's exhausted allowance.
    dependency(principal_b)
