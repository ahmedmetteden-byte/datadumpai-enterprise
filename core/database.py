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


@lru_cache(maxsize=1)
def _service_role_client():
    from supabase import create_client

    if not SUPABASE_SERVICE_ROLE_KEY:
        raise DatabaseError(
            "SUPABASE_SERVICE_ROLE_KEY is required for database access in development."
        )

    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


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
        return _service_role_client()

    if not token:
        raise DatabaseError("No authenticated session is available for database access.")

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(token)
    return client


def handle_response(response: Any, *, action: str) -> Any:
    """Raise a readable error when Supabase returns an API failure."""

    error = getattr(response, "error", None)
    if error:
        message = getattr(error, "message", None) or str(error)
        raise DatabaseError(f"Could not {action}: {message}")
    return response
