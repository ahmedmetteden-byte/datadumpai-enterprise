"""
Temporary debug tracing for the password recovery callback flow.

Enable with RECOVERY_CALLBACK_TRACE=true or DEBUG=true in the environment.
Logs append to data/recovery_callback_trace.log and print to stderr.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import streamlit as st

from core.auth import (
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_RECOVERY_MODE_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AUTH_USER_KEY,
    AUTH_VIEW_KEY,
)

RecoveryBranch = Literal["pkce", "otp", "none"]

_LOG_PATH = Path("data") / "recovery_callback_trace.log"
_SESSION_TRACE_KEY = "_recovery_callback_trace_events"


def trace_enabled() -> bool:
    flag = os.getenv("RECOVERY_CALLBACK_TRACE", "").lower() in {"1", "true", "yes"}
    debug = os.getenv("DEBUG", "").lower() in {"1", "true", "yes"}
    return flag or debug


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_secret(value: str | None) -> dict[str, Any]:
    if not value:
        return {"present": False, "length": 0}
    return {
        "present": True,
        "length": len(value),
        "prefix": value[:8],
    }


def _query_value(params, key: str) -> str | None:
    value = params.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def snapshot_query_params() -> dict[str, Any]:
    params = st.query_params
    return {
        "type": _query_value(params, "type"),
        "code": _mask_secret(_query_value(params, "code")),
        "token_hash": _mask_secret(_query_value(params, "token_hash")),
        "access_token": _mask_secret(_query_value(params, "access_token")),
        "refresh_token": _mask_secret(_query_value(params, "refresh_token")),
        "active_page": _query_value(params, "active_page"),
        "error": _query_value(params, "error"),
        "error_description": _query_value(params, "error_description"),
        "raw_query_keys": sorted(params.keys()) if hasattr(params, "keys") else [],
    }


def select_recovery_branch(
    *,
    code: str | None,
    token_hash: str | None,
    access_token: str | None = None,
    refresh_token: str | None = None,
) -> RecoveryBranch:
    """Choose recovery exchange path from query params (code / token_hash only)."""

    _ = (access_token, refresh_token)
    if token_hash:
        return "otp"
    if code:
        return "pkce"
    return "none"


def snapshot_auth_state() -> dict[str, Any]:
    return {
        "auth_recovery_mode": bool(st.session_state.get(AUTH_RECOVERY_MODE_KEY)),
        "auth_view": st.session_state.get(AUTH_VIEW_KEY),
        "auth_user_present": st.session_state.get(AUTH_USER_KEY) is not None,
        "auth_access_token": _mask_secret(st.session_state.get(AUTH_ACCESS_TOKEN_KEY)),
        "auth_refresh_token": _mask_secret(st.session_state.get(AUTH_REFRESH_TOKEN_KEY)),
        "auth_recovery_failed": bool(st.session_state.get("auth_recovery_failed")),
        "auth_error_set": bool(st.session_state.get("auth_error")),
        "active_page": st.session_state.get("active_page"),
        "hash_promotion_attempts": None,  # hash promotion removed; kept for log shape
    }


def explain_sign_in_render() -> dict[str, Any]:
    recovery_mode = bool(st.session_state.get(AUTH_RECOVERY_MODE_KEY))
    auth_view = st.session_state.get(AUTH_VIEW_KEY, "sign_in")
    recovery_failed = bool(st.session_state.get("auth_recovery_failed"))
    auth_error = st.session_state.get("auth_error")
    active_page = st.session_state.get("active_page")

    reasons: list[str] = []
    if recovery_mode:
        reasons.append("auth_recovery_mode is True — should render Reset Password, not Sign In")
    else:
        reasons.append("auth_recovery_mode is False")

    if auth_view == "sign_in":
        reasons.append(f"auth_view is 'sign_in'")
    elif auth_view == "reset_password":
        reasons.append("auth_view is 'reset_password'")

    if recovery_failed:
        reasons.append("auth_recovery_failed is True — Sign In shown with resend CTA")
    if auth_error:
        reasons.append(f"auth_error is set: {auth_error!r}")

    if active_page != "auth":
        reasons.append(
            f"active_page is '{active_page}' (not 'auth') — auth gate may not run"
        )

    return {
        "renders_sign_in": not recovery_mode and auth_view == "sign_in",
        "renders_reset_password": recovery_mode or auth_view == "reset_password",
        "reasons": reasons,
    }


def log_recovery_trace(step: str, **payload: Any) -> None:
    if not trace_enabled():
        return

    entry = {
        "timestamp": _utc_now(),
        "step": step,
        "query_params": snapshot_query_params(),
        "auth_state": snapshot_auth_state(),
        **payload,
    }

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str) + "\n")

    trace_events = st.session_state.setdefault(_SESSION_TRACE_KEY, [])
    trace_events.append({"step": step, **{k: v for k, v in payload.items() if k != "query_params"}})

    print(f"[RECOVERY_CALLBACK_TRACE] {step}", file=sys.stderr)
    for key, value in payload.items():
        print(f"  {key}: {value}", file=sys.stderr)


def log_supabase_exchange(
    *,
    operation: str,
    branch: RecoveryBranch,
    success: bool,
    session_returned: bool | None = None,
    user_returned: bool | None = None,
    error: str | None = None,
    exception_type: str | None = None,
) -> None:
    log_recovery_trace(
        f"supabase.{operation}",
        branch=branch,
        supabase_success=success,
        session_returned=session_returned,
        user_returned=user_returned,
        supabase_error=error,
        exception_type=exception_type,
    )
