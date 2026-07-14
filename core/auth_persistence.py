"""
Persist auth tokens in browser cookies when the user chooses Remember me.
"""

from __future__ import annotations

import json
from functools import lru_cache

import streamlit as st

import config
from config import DEBUG

AUTH_COOKIE_NAME = "datadumpai_auth"
AUTH_COOKIES_LOADED_KEY = "auth_cookies_loaded"


_COOKIE_MANAGER_MISSING_MSG = (
    "Authentication dependency is missing. "
    "Run: pip install extra-streamlit-components"
)


@lru_cache(maxsize=1)
def _try_cookie_manager():
    """Return a cookie manager when available; never stop the app."""

    try:
        from extra_streamlit_components import CookieManager
    except ImportError:
        return None

    try:
        return CookieManager()
    except Exception:
        return None


@lru_cache(maxsize=1)
def _cookie_manager():
    manager = _try_cookie_manager()
    if manager is None:
        st.error(_COOKIE_MANAGER_MISSING_MSG)
        st.stop()

    return manager


def cookies_are_ready() -> bool:
    """Return True once the browser cookie jar has been read."""

    if config.auth_dev_bypass_enabled():
        return True

    if st.session_state.get(AUTH_COOKIES_LOADED_KEY):
        return True

    cookies = _cookie_manager().get_all()
    if cookies is None:
        return False

    st.session_state[AUTH_COOKIES_LOADED_KEY] = True
    return True


def persist_auth_tokens(access_token: str, refresh_token: str) -> None:
    """Store tokens in a secure, SameSite cookie."""

    if config.auth_dev_bypass_enabled():
        return

    payload = json.dumps({"access": access_token, "refresh": refresh_token})
    _cookie_manager().set(
        AUTH_COOKIE_NAME,
        payload,
        max_age=60 * 60 * 24 * 30,
        secure=not DEBUG,
        same_site="strict",
    )


def restore_persisted_tokens() -> tuple[str, str] | None:
    """Read persisted tokens from cookies, if present."""

    if config.auth_dev_bypass_enabled() or not cookies_are_ready():
        return None

    raw = _cookie_manager().get(AUTH_COOKIE_NAME)
    if not raw:
        return None

    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        clear_persisted_tokens()
        return None

    access = payload.get("access")
    refresh = payload.get("refresh")
    if not access or not refresh:
        return None

    return str(access), str(refresh)


def clear_persisted_tokens() -> None:
    """Remove persisted auth tokens from the browser (best-effort)."""

    if config.auth_dev_bypass_enabled():
        return

    manager = _try_cookie_manager()
    if manager is None:
        return

    try:
        manager.delete(AUTH_COOKIE_NAME)
    except KeyError:
        return
    except Exception:
        return
