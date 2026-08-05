"""
Supabase JWT validation for the product API.

Current Supabase projects issue ES256 access tokens. Verification uses the
project JWKS endpoint (public keys), not a shared HS256 secret.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from models.user import User

logger = logging.getLogger(__name__)

EXPECTED_AUDIENCE = "authenticated"
ALLOWED_ALGORITHMS = ("ES256",)

# Cached JWKS client (PyJWKClient caches key sets for ``lifespan`` seconds).
_jwks_client: PyJWKClient | None = None
_jwks_client_url: str | None = None


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: User
    access_token: str


def _supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")


def _jwks_url() -> str:
    base = _supabase_url()
    if not base:
        return ""
    return f"{base}/auth/v1/.well-known/jwks.json"


def _expected_issuer() -> str:
    base = _supabase_url()
    if not base:
        return ""
    return f"{base}/auth/v1"


def _get_jwks_client() -> PyJWKClient:
    """Return a process-wide PyJWKClient with key-set caching."""

    global _jwks_client, _jwks_client_url

    url = _jwks_url()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SUPABASE_URL is not configured on the API server. "
                "Set it in the repository root .env, then restart the API."
            ),
        )

    if _jwks_client is None or _jwks_client_url != url:
        # lifespan: seconds to cache the JWKS document before refresh.
        _jwks_client = PyJWKClient(
            url,
            cache_keys=True,
            lifespan=3600,
            timeout=10,
        )
        _jwks_client_url = url
        logger.info(
            "JWKS client initialised | url=%s | cache_lifespan_s=%s | algorithms=%s",
            url,
            3600,
            list(ALLOWED_ALGORITHMS),
        )

    return _jwks_client


def _classify_jwt_error(exc: Exception) -> str:
    """Map PyJWT exceptions to a safe diagnostic label (no token content)."""

    name = type(exc).__name__
    if isinstance(exc, jwt.ExpiredSignatureError):
        return "expired"
    if isinstance(exc, jwt.InvalidAudienceError):
        return "wrong_audience"
    if isinstance(exc, jwt.InvalidIssuerError):
        return "wrong_issuer"
    if isinstance(exc, jwt.InvalidSignatureError):
        return "invalid_signature"
    if isinstance(exc, jwt.DecodeError):
        return "malformed_token"
    if isinstance(exc, jwt.InvalidAlgorithmError):
        return "invalid_algorithm"
    if isinstance(exc, jwt.ImmatureSignatureError):
        return "token_not_yet_valid"
    if isinstance(exc, PyJWKClientError):
        return f"jwks_error ({name})"
    if isinstance(exc, jwt.InvalidTokenError):
        return f"invalid_token ({name})"
    return f"jwt_error ({name})"


def _safe_token_meta(token: str) -> tuple[str | None, dict]:
    """Unverified header/claims for diagnostics — never log the token."""

    alg: str | None = None
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
    except Exception:  # noqa: BLE001 — diagnostic only
        alg = None

    try:
        unverified = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
                "verify_iss": False,
            },
        )
        meta = {
            "has_sub": bool(unverified.get("sub")),
            "aud": unverified.get("aud"),
            "iss": unverified.get("iss"),
            "role": unverified.get("role"),
            "has_exp": "exp" in unverified,
            "exp": unverified.get("exp"),
        }
    except Exception as peek_exc:  # noqa: BLE001 — diagnostic only
        meta = {"peek_failed": type(peek_exc).__name__}

    return alg, meta


def decode_supabase_token(token: str) -> AuthenticatedPrincipal:
    """Validate a Supabase access token and return the authenticated user.

    Mechanism: ES256 signature verify via project JWKS (PyJWT ``PyJWKClient``).
    Also enforces issuer, audience ``authenticated``, and expiration.
    """

    issuer = _expected_issuer()
    jwks = _jwks_url()
    alg, token_meta = _safe_token_meta(token)

    logger.info(
        "JWT verify diagnostic: mechanism=JWKS+ES256 "
        "jwks_url=%s issuer_expected=%s audience_expected=%s "
        "supabase_url_configured=%s",
        jwks or "(missing)",
        issuer or "(missing)",
        EXPECTED_AUDIENCE,
        bool(_supabase_url()),
    )

    if not issuer:
        logger.error("JWT validation aborted: SUPABASE_URL is not set.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SUPABASE_URL is not configured on the API server. "
                "Set it in the repository root .env, then restart the API."
            ),
        )

    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=EXPECTED_AUDIENCE,
            issuer=issuer,
            options={
                "require": ["exp", "sub", "aud", "iss"],
            },
        )
    except (jwt.PyJWTError, PyJWKClientError) as exc:
        reason = _classify_jwt_error(exc)
        logger.exception(
            "JWT validation failed | "
            "exception_type=%s | "
            "exception_message=%s | "
            "reason=%s | "
            "algorithm=%s | "
            "issuer=%s | "
            "audience=%s | "
            "expected_issuer=%s | "
            "expected_audience=%s | "
            "expected_algorithms=%s | "
            "verification=JWKS+ES256 | "
            "jwks_url=%s | "
            "repr=%r",
            type(exc).__name__,
            str(exc),
            reason,
            alg,
            token_meta.get("iss") if isinstance(token_meta, dict) else None,
            token_meta.get("aud") if isinstance(token_meta, dict) else None,
            issuer,
            EXPECTED_AUDIENCE,
            list(ALLOWED_ALGORITHMS),
            jwks,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    logger.info(
        "JWT verified | sub_present=%s | algorithm=%s | issuer=%s | audience=%s",
        bool(payload.get("sub")),
        alg,
        payload.get("iss"),
        payload.get("aud"),
    )

    user_id = str(payload.get("sub") or "").strip()
    email = str(payload.get("email") or "").strip()
    if not user_id:
        logger.warning(
            "JWT validation failed: reason=missing_subject meta=%s",
            token_meta,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
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
