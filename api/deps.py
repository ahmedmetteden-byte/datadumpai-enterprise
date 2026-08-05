"""
FastAPI dependencies for the product API.

Protected routes should depend on ``get_principal`` (token + user) or
``get_current_user`` (user only). Both validate the Supabase JWT.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from api.auth_jwt import AuthenticatedPrincipal, decode_supabase_token
from core.current_user import CurrentUser, current_user_scope
from models.user import User
from services.document_service import DocumentService
from services.project_service import ProjectService

logger = logging.getLogger(__name__)


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """Extract the Bearer token. Logs header presence only — never the token."""

    if not authorization:
        logger.warning(
            "Auth header diagnostic: Authorization missing "
            "(will return 401 Authorization header required)."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    scheme_ok = scheme.lower() == "bearer"
    token_present = bool(token.strip())
    logger.warning(
        "Auth header diagnostic: present=True scheme=%r scheme_ok=%s "
        "token_present=%s token_length=%s",
        scheme,
        scheme_ok,
        token_present,
        len(token.strip()) if token_present else 0,
    )

    if not scheme_ok or not token_present:
        logger.warning(
            "Auth header diagnostic: Bearer token rejected "
            "(scheme_ok=%s token_present=%s).",
            scheme_ok,
            token_present,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def get_principal(
    token: str = Depends(get_bearer_token),
) -> AuthenticatedPrincipal:
    """Validate the Supabase access token and return the authenticated principal."""

    return decode_supabase_token(token)


def get_current_user(
    principal: AuthenticatedPrincipal = Depends(get_principal),
) -> User:
    """Reusable dependency: validates Supabase JWT and provides ``current_user``."""

    return principal.user


# Convenience aliases for Annotated dependency injection.
PrincipalDep = Annotated[AuthenticatedPrincipal, Depends(get_principal)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@contextmanager
def user_request_scope(principal: AuthenticatedPrincipal) -> Iterator[CurrentUser]:
    """Bind CurrentUser for the duration of a request handler."""

    with current_user_scope(principal.user) as current:
        yield current


def project_service_for(principal: AuthenticatedPrincipal) -> ProjectService:
    with user_request_scope(principal):
        return ProjectService(access_token=principal.access_token)


def document_service_for(principal: AuthenticatedPrincipal) -> DocumentService:
    with user_request_scope(principal):
        return DocumentService(access_token=principal.access_token)


# Backwards-compatible alias
require_user = get_current_user
