"""
FastAPI dependencies for the product API.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import Depends, Header, HTTPException, status

from api.auth_jwt import AuthenticatedPrincipal, decode_supabase_token
from core.current_user import CurrentUser, current_user_scope
from models.user import User
from services.document_service import DocumentService
from services.project_service import ProjectService


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required.",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
        )
    return token.strip()


def get_principal(token: str = Depends(get_bearer_token)) -> AuthenticatedPrincipal:
    return decode_supabase_token(token)


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


def require_user(principal: AuthenticatedPrincipal = Depends(get_principal)) -> User:
    return principal.user
