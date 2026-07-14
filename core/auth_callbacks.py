"""
Supabase auth callback helpers for email links and password recovery.

Recovery uses query-parameter callbacks only (PKCE ``code`` or ``token_hash``).
Hash-fragment / implicit-token promotion is intentionally not supported.
"""

from __future__ import annotations

import streamlit as st

from core.auth import (
    AUTH_RECOVERY_MODE_KEY,
    AUTH_VIEW_KEY,
    _store_recovery_session,
)
from services.auth_service import AuthError, AuthService, AuthSession

_AUTH_RECOVERY_FAILED_KEY = "auth_recovery_failed"

RECOVERY_LINK_INVALID_MESSAGE = (
    "This password reset link is invalid or has expired. "
    "Request a new reset email below."
)


def _query_value(params, key: str) -> str | None:
    value = params.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def has_actionable_auth_query_params() -> bool:
    """Return True when the query string contains a processable auth callback."""

    params = st.query_params
    auth_type = _query_value(params, "type")
    code = _query_value(params, "code")
    token_hash = _query_value(params, "token_hash")

    if auth_type == "recovery" and (code or token_hash):
        return True

    if code and auth_type in {"signup", "email", "magiclink"}:
        return True

    if _query_value(params, "error") or _query_value(params, "error_description"):
        return True

    return False


def _fail_recovery_callback(message: str) -> None:
    from core.recovery_callback_trace import log_recovery_trace

    log_recovery_trace(
        "recovery.fail",
        message=message,
        cleared_recovery_mode=True,
        auth_view_set_to="sign_in",
    )
    st.session_state[AUTH_VIEW_KEY] = "sign_in"
    st.session_state.auth_error = message
    st.session_state[_AUTH_RECOVERY_FAILED_KEY] = True
    st.session_state[AUTH_RECOVERY_MODE_KEY] = False
    _clear_auth_callback_params()


def _establish_recovery_session_from_callback(
    *,
    code: str | None,
    token_hash: str | None,
) -> AuthSession:
    from core.recovery_callback_trace import log_recovery_trace, select_recovery_branch

    branch = select_recovery_branch(
        code=code,
        token_hash=token_hash,
        access_token=None,
        refresh_token=None,
    )
    log_recovery_trace("recovery.branch_selected", branch=branch)

    service = AuthService()

    try:
        if token_hash:
            return service.exchange_recovery_token_hash(token_hash)
        if code:
            return service.exchange_recovery_code(code)
    except AuthError as exc:
        log_recovery_trace(
            "recovery.exchange_auth_error",
            branch=branch,
            error=str(exc),
        )
        raise
    except Exception as exc:
        log_recovery_trace(
            "recovery.exchange_exception",
            branch=branch,
            exception_type=type(exc).__name__,
            error=str(exc),
        )
        raise AuthError(RECOVERY_LINK_INVALID_MESSAGE) from exc

    log_recovery_trace("recovery.branch_none", branch=branch)
    raise AuthError(RECOVERY_LINK_INVALID_MESSAGE)


def handle_auth_callback_query_params() -> bool:
    """
    Process Supabase email-link callbacks.

    Returns True when a recovery callback was handled.
    """

    from core.recovery_callback_trace import log_recovery_trace, select_recovery_branch

    params = st.query_params
    auth_type = _query_value(params, "type")
    code = _query_value(params, "code")
    token_hash = _query_value(params, "token_hash")
    error_description = _query_value(params, "error_description")
    error = _query_value(params, "error")

    log_recovery_trace(
        "callback.enter",
        auth_type=auth_type,
        branch=select_recovery_branch(
            code=code,
            token_hash=token_hash,
            access_token=None,
            refresh_token=None,
        ),
    )

    if auth_type != "recovery":
        log_recovery_trace("callback.exit", handled=False, reason="auth_type_not_recovery")
        return False

    if error or error_description:
        log_recovery_trace(
            "callback.supabase_error_param",
            error=error,
            error_description=error_description,
        )
        _fail_recovery_callback(
            error_description or error or RECOVERY_LINK_INVALID_MESSAGE
        )
        return True

    if not code and not token_hash:
        log_recovery_trace(
            "callback.exit",
            handled=False,
            reason="recovery_type_without_actionable_tokens",
        )
        return False

    try:
        session = _establish_recovery_session_from_callback(
            code=code,
            token_hash=token_hash,
        )
    except AuthError as exc:
        log_recovery_trace("callback.exchange_failed", error=str(exc))
        _fail_recovery_callback(str(exc))
        return True
    except Exception as exc:
        log_recovery_trace(
            "callback.exchange_failed",
            exception_type=type(exc).__name__,
            error=str(exc),
        )
        _fail_recovery_callback(RECOVERY_LINK_INVALID_MESSAGE)
        return True

    log_recovery_trace(
        "callback.exchange_success",
        session_returned=True,
        user_id=session.user.id,
    )
    _store_recovery_session(session)
    st.session_state.pop(_AUTH_RECOVERY_FAILED_KEY, None)
    _clear_auth_callback_params()
    log_recovery_trace(
        "callback.success",
        handled=True,
        auth_recovery_mode_after=True,
        auth_view_after="reset_password",
    )
    return True


def handle_email_verification_query_params() -> bool:
    """Process signup / email verification callbacks."""

    params = st.query_params
    auth_type = _query_value(params, "type")
    code = _query_value(params, "code")

    if not code or auth_type not in {"signup", "email", "magiclink"}:
        return False

    from core.auth import _store_session

    try:
        session = AuthService().exchange_auth_code(code)
        _store_session(session, remember_me=True)
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
        st.session_state.auth_success = "Email verified. Welcome to DataDumpAI."
    except AuthError:
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
        st.session_state.auth_error = (
            "This verification link is invalid or has expired."
        )
    except Exception:
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
        st.session_state.auth_error = (
            "This verification link is invalid or has expired."
        )

    _clear_auth_callback_params()
    return True


def recovery_failed() -> bool:
    return bool(st.session_state.get(_AUTH_RECOVERY_FAILED_KEY))


def _clear_auth_callback_params() -> None:
    for key in (
        "type",
        "code",
        "token_hash",
        "access_token",
        "refresh_token",
        "expires_in",
        "token_type",
        "error",
        "error_description",
    ):
        if key in st.query_params:
            del st.query_params[key]
