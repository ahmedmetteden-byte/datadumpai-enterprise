"""
Supabase JWT validation for the product API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status

from models.user import User


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: User
    access_token: str


def _jwt_secret() -> str:
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if secret:
        return secret
    # Fallback used by some local setups; prefer SUPABASE_JWT_SECRET in production.
    return os.getenv("SUPABASE_ANON_KEY", "").strip()


def decode_supabase_token(token: str) -> AuthenticatedPrincipal:
    """Validate a Supabase access token and return the authenticated user."""

    secret = _jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_JWT_SECRET is not configured on the API server.",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc

    user_id = str(payload.get("sub") or "").strip()
    email = str(payload.get("email") or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing subject.",
        )

    meta = payload.get("user_metadata") or {}
    full_name = ""
    if isinstance(meta, dict):
        full_name = str(meta.get("full_name") or meta.get("fullName") or "").strip()

    user = User(
        id=user_id,
        email=email,
        full_name=full_name or None,
        email_verified=bool(payload.get("email_confirmed_at") or payload.get("aal")),
    )
    return AuthenticatedPrincipal(user=user, access_token=token)
