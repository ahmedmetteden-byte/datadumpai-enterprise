"""
Mandatory authenticated-user context for multi-tenant services.

Services must obtain the active user via ``require_current_user()`` instead of
accepting a raw ``user_id`` from callers. If no authenticated user is available,
access fails closed.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from models.user import User


class AuthenticationRequiredError(RuntimeError):
    """Raised when an authenticated user is required but unavailable."""


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Authenticated user bound to the current request or session."""

    id: str
    email: str
    full_name: str | None = None
    email_verified: bool = False

    @classmethod
    def from_user(cls, user: User) -> CurrentUser:
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            email_verified=user.email_verified,
        )

    @property
    def display_name(self) -> str:
        return self.full_name or self.email or self.id


_current_user_override: ContextVar[CurrentUser | None] = ContextVar(
    "current_user_override",
    default=None,
)


def require_current_user() -> CurrentUser:
    """Return the authenticated user or fail closed."""

    override = _current_user_override.get()
    if override is not None:
        return override

    from core.auth import get_current_user

    user = get_current_user()
    if user is None:
        raise AuthenticationRequiredError(
            "Authentication is required to access this resource."
        )

    return CurrentUser.from_user(user)


def get_current_user_optional() -> CurrentUser | None:
    """Return the authenticated user when present, otherwise ``None``."""

    override = _current_user_override.get()
    if override is not None:
        return override

    from core.auth import get_current_user

    user = get_current_user()
    if user is None:
        return None

    return CurrentUser.from_user(user)


def current_user_id() -> str:
    """Return the authenticated user's id or fail closed."""

    return require_current_user().id


@contextmanager
def current_user_scope(user: User | CurrentUser) -> Iterator[CurrentUser]:
    """Bind a user for the duration of a block (tests and bootstrap)."""

    current = user if isinstance(user, CurrentUser) else CurrentUser.from_user(user)
    token = _current_user_override.set(current)
    try:
        yield current
    finally:
        _current_user_override.reset(token)


def bind_current_user(user: User | CurrentUser) -> None:
    """Bind a user for the remainder of the current context (tests)."""

    current = user if isinstance(user, CurrentUser) else CurrentUser.from_user(user)
    _current_user_override.set(current)


def clear_current_user_binding() -> None:
    """Clear any test override for the current user."""

    _current_user_override.set(None)
