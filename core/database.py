"""
Supabase PostgreSQL client for authenticated application queries.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import config
from config import (
    SUPABASE_ANON_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
    is_supabase_configured,
    use_database,
)


class DatabaseError(Exception):
    """Raised when a database operation fails."""


def database_is_available() -> bool:
    return use_database() and is_supabase_configured()


def create_service_role_client():
    """
    Create a fresh service-role Supabase client for admin/server operations.

    Always disables session persistence so a user sign-in cannot overwrite the
    service-role Authorization header (a known supabase-py footgun).
    """

    from supabase import ClientOptions, create_client

    # Read at call time — avoid stale empty keys from import-time binding.
    url = (config.SUPABASE_URL or "").strip()
    key = (config.SUPABASE_SERVICE_ROLE_KEY or "").strip()
    if not url or not key:
        raise DatabaseError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for "
            "service-role database access."
        )

    client = create_client(
        url,
        key,
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        ),
    )
    # Belt-and-suspenders: keep admin calls on the service-role Bearer token.
    client.options.headers["apiKey"] = key
    client.options.headers["Authorization"] = f"Bearer {key}"
    return client


@lru_cache(maxsize=1)
def _service_role_client():
    return create_service_role_client()


def get_service_role_client():
    """Return a Supabase client with service-role access (server-side only)."""

    if not is_supabase_configured():
        raise DatabaseError("Supabase is not configured.")
    return _service_role_client()


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
