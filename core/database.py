"""
Supabase PostgreSQL client for authenticated application queries.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import config
from config import (
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    is_supabase_configured,
    use_database,
)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when a database operation fails."""


def database_is_available() -> bool:
    return use_database() and is_supabase_configured()


def _service_role_credentials() -> tuple[str, str]:
    url = (config.SUPABASE_URL or "").strip().rstrip("/")
    key = (config.SUPABASE_SERVICE_ROLE_KEY or "").strip()
    if not url or not key:
        raise DatabaseError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for "
            "service-role database access."
        )
    return url, key


def _apply_service_role_headers(client: Any, key: str) -> None:
    """Keep Authorization on both PostgREST and GoTrue admin clients."""

    headers = {
        "apiKey": key,
        "Authorization": f"Bearer {key}",
    }
    client.options.headers.update(headers)

    auth = getattr(client, "auth", None)
    if auth is None:
        return

    auth_headers = getattr(auth, "_headers", None)
    if isinstance(auth_headers, dict):
        auth_headers.update(headers)

    admin = getattr(auth, "admin", None)
    admin_headers = getattr(admin, "_headers", None) if admin is not None else None
    if isinstance(admin_headers, dict):
        admin_headers.update(headers)


def create_service_role_client():
    """
    Create a fresh service-role Supabase client for admin/server operations.

    Always disables session persistence so a user sign-in cannot overwrite the
    service-role Authorization header (a known supabase-py footgun).
    """

    from supabase import ClientOptions, create_client

    url, key = _service_role_credentials()
    client = create_client(
        url,
        key,
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        ),
    )
    _apply_service_role_headers(client, key)
    return client


def _admin_api_headers(key: str) -> dict[str, str]:
    """
    Headers for Supabase Auth Admin HTTP calls.

    New ``sb_secret_...`` keys are not JWTs. Always send them on ``apikey``.
    Also send ``Authorization: Bearer <key>`` (required by GoTrue admin routes
    and accepted when it matches ``apikey``). Use a non-browser User-Agent —
    secret keys are rejected when the platform detects a browser UA.
    """

    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "DataDumpAI-Enterprise/1.0",
        "X-Client-Info": "datadumpai-enterprise-admin",
    }


def _log_admin_request(
    *,
    method: str,
    endpoint: str,
    headers: dict[str, str],
    service_role_key: str,
    response: Any,
) -> None:
    """Log non-secret evidence about Auth Admin HTTP calls."""

    from core.signup_trace import signup_trace_log

    auth_header = headers.get("Authorization", "")
    signup_trace_log(logger, "SIGNUP_TRACE Admin endpoint: %s %s", method, endpoint)
    signup_trace_log(
        logger,
        "SIGNUP_TRACE Authorization header present: %s",
        "Authorization" in headers,
    )
    signup_trace_log(
        logger,
        "SIGNUP_TRACE Authorization starts with Bearer: %s",
        auth_header.startswith("Bearer "),
    )
    signup_trace_log(
        logger, "SIGNUP_TRACE Service role key length: %d", len(service_role_key)
    )
    signup_trace_log(
        logger,
        "SIGNUP_TRACE Service role key prefix kind: %s",
        (
            "jwt"
            if service_role_key.startswith("eyJ")
            else "sb_secret"
            if service_role_key.startswith("sb_secret_")
            else "other"
        ),
    )
    signup_trace_log(
        logger, "SIGNUP_TRACE apikey header present: %s", "apikey" in headers
    )
    signup_trace_log(logger, "SIGNUP_TRACE Status: %d", response.status_code)
    signup_trace_log(logger, "SIGNUP_TRACE Body: %s", (response.text or "")[:500])


def _raise_admin_http_error(response: Any) -> None:
    detail = response.text
    try:
        payload = response.json()
        detail = payload.get("msg") or payload.get("message") or detail
    except Exception:
        pass
    raise DatabaseError(detail)


def admin_create_user(
    *,
    email: str,
    password: str,
    full_name: str = "",
    email_confirm: bool = True,
) -> dict[str, Any]:
    """
    Create an auth user via the Admin HTTP API with an explicit Bearer token.

    Bypasses supabase-py session/header mutation bugs that can drop Authorization
    and surface: "This endpoint requires a valid Bearer token".
    """

    import httpx

    url, key = _service_role_credentials()
    endpoint = f"{url}/auth/v1/admin/users"
    headers = _admin_api_headers(key)
    response = httpx.post(
        endpoint,
        headers=headers,
        json={
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
            "user_metadata": {"full_name": full_name.strip()},
        },
        timeout=30.0,
    )
    _log_admin_request(
        method="POST",
        endpoint=endpoint,
        headers=headers,
        service_role_key=key,
        response=response,
    )
    if response.status_code >= 400:
        _raise_admin_http_error(response)
    return response.json()


def admin_update_user(user_id: str, attributes: dict[str, Any]) -> dict[str, Any]:
    """Update an auth user via the Admin HTTP API with an explicit Bearer token."""

    import httpx

    url, key = _service_role_credentials()
    endpoint = f"{url}/auth/v1/admin/users/{user_id}"
    headers = _admin_api_headers(key)
    response = httpx.put(
        endpoint,
        headers=headers,
        json=attributes,
        timeout=30.0,
    )
    _log_admin_request(
        method="PUT",
        endpoint=endpoint,
        headers=headers,
        service_role_key=key,
        response=response,
    )
    if response.status_code >= 400:
        _raise_admin_http_error(response)
    return response.json()


def admin_get_user_by_email(email: str) -> dict[str, Any] | None:
    """Look up an auth user by email via the Admin HTTP API."""

    import httpx

    url, key = _service_role_credentials()
    normalized = email.strip().lower()
    endpoint = f"{url}/auth/v1/admin/users"
    headers = _admin_api_headers(key)
    response = httpx.get(
        endpoint,
        headers=headers,
        params={"filter": normalized, "page": 1, "per_page": 50},
        timeout=30.0,
    )
    _log_admin_request(
        method="GET",
        endpoint=endpoint,
        headers=headers,
        service_role_key=key,
        response=response,
    )
    if response.status_code >= 400:
        _raise_admin_http_error(response)

    users = response.json().get("users") or []
    for user in users:
        if str(user.get("email") or "").strip().lower() == normalized:
            return user
    return None


@lru_cache(maxsize=1)
def _service_role_client():
    return create_service_role_client()


def get_service_role_client():
    """Return a Supabase client with service-role access (server-side only)."""

    if not is_supabase_configured():
        raise DatabaseError("Supabase is not configured.")
    # Never reuse a poisoned client across Streamlit reruns.
    _service_role_client.cache_clear()
    return create_service_role_client()


def get_database_client(*, access_token: str | None = None):
    """
    Return a Supabase client scoped to the signed-in user.

    Uses the user's JWT for RLS in production. Development bypass falls back
    to the service role key with explicit user_id filters in repositories.
    """

    if not database_is_available():
        raise DatabaseError("Database backend is not enabled.")

    from supabase import create_client

    from core.auth import get_access_token

    token = access_token or get_access_token()

    if config.auth_dev_bypass_enabled():
        return create_service_role_client()

    if not token:
        raise DatabaseError("No authenticated session is available for database access.")

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    # Apply the user JWT to shared client headers so Storage (and PostgREST)
    # both use the authenticated session — not only postgrest.auth().
    auth_header = f"Bearer {token}"
    client.options.headers["Authorization"] = auth_header
    client.postgrest.auth(token)
    # Ensure lazily-created Storage picks up the updated headers.
    client._storage = None
    return client


def handle_response(response: Any, *, action: str) -> Any:
    """Raise a readable error when Supabase returns an API failure."""

    error = getattr(response, "error", None)
    if error:
        message = getattr(error, "message", None) or str(error)
        raise DatabaseError(f"Could not {action}: {message}")
    return response
