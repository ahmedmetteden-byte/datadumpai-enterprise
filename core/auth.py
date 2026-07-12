"""
Authentication session management for Streamlit.
"""

from __future__ import annotations

import streamlit as st

import config
from config import AUTH_DEV_BYPASS, is_supabase_configured
from core.telemetry import identify, track
from models.user import User
from services.auth_service import AuthError, AuthService, AuthSession

AUTH_USER_KEY = "auth_user"
AUTH_ACCESS_TOKEN_KEY = "auth_access_token"
AUTH_REFRESH_TOKEN_KEY = "auth_refresh_token"
AUTH_REMEMBER_ME_KEY = "auth_remember_me"
AUTH_VIEW_KEY = "auth_view"
AUTH_PENDING_EMAIL_KEY = "auth_pending_email"
AUTH_RECOVERY_MODE_KEY = "auth_recovery_mode"
AUTH_BOOTSTRAP_PENDING_KEY = "auth_bootstrap_pending"


def initialize_auth() -> None:
    """Restore an existing session and handle auth deep links."""

    if AUTH_USER_KEY not in st.session_state:
        st.session_state[AUTH_USER_KEY] = None
    if AUTH_ACCESS_TOKEN_KEY not in st.session_state:
        st.session_state[AUTH_ACCESS_TOKEN_KEY] = None
    if AUTH_REFRESH_TOKEN_KEY not in st.session_state:
        st.session_state[AUTH_REFRESH_TOKEN_KEY] = None
    if AUTH_VIEW_KEY not in st.session_state:
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
    if AUTH_RECOVERY_MODE_KEY not in st.session_state:
        st.session_state[AUTH_RECOVERY_MODE_KEY] = False

    _handle_auth_query_params()

    if st.session_state[AUTH_USER_KEY] is not None:
        return

    access_token = st.session_state.get(AUTH_ACCESS_TOKEN_KEY)
    refresh_token = st.session_state.get(AUTH_REFRESH_TOKEN_KEY)

    if access_token and refresh_token:
        try:
            session = AuthService().restore_session(access_token, refresh_token)
            _store_session(session, remember_me=st.session_state.get(AUTH_REMEMBER_ME_KEY, False))
        except AuthError:
            clear_auth_session()
        return

    _restore_persisted_session()


def _restore_persisted_session() -> None:
    """Restore a session from browser cookies when Remember me was enabled."""

    if AUTH_DEV_BYPASS:
        return

    from core.auth_persistence import cookies_are_ready, restore_persisted_tokens

    if not cookies_are_ready():
        return

    tokens = restore_persisted_tokens()
    if tokens is None:
        return

    access_token, refresh_token = tokens
    try:
        session = AuthService().restore_session(access_token, refresh_token)
        st.session_state[AUTH_REMEMBER_ME_KEY] = True
        _store_session(session, remember_me=True)
    except AuthError:
        from core.auth_persistence import clear_persisted_tokens

        clear_persisted_tokens()


def _handle_auth_query_params() -> None:
    """Handle Supabase email links for verification and password recovery."""

    params = st.query_params
    auth_type = params.get("type")
    code = params.get("code")

    if not code:
        return

    if auth_type == "recovery":
        try:
            session = AuthService().exchange_recovery_code(code)
            _store_session(session, remember_me=False)
            st.session_state[AUTH_RECOVERY_MODE_KEY] = True
            st.session_state[AUTH_VIEW_KEY] = "reset_password"
            st.query_params.clear()
        except AuthError:
            st.session_state[AUTH_VIEW_KEY] = "sign_in"
            st.session_state.auth_error = (
                "This password reset link is invalid or has expired."
            )
        return

    if auth_type in {"signup", "email", "magiclink"}:
        try:
            session = AuthService().exchange_auth_code(code)
            _store_session(session, remember_me=True)
            st.session_state[AUTH_VIEW_KEY] = "sign_in"
            st.session_state.auth_success = (
                "Email verified. Welcome to DataDumpAI."
            )
            st.query_params.clear()
        except AuthError:
            st.session_state[AUTH_VIEW_KEY] = "sign_in"
            st.session_state.auth_error = (
                "This verification link is invalid or has expired."
            )


def is_authenticated() -> bool:
    initialize_auth()
    return st.session_state.get(AUTH_USER_KEY) is not None


def get_current_user() -> User | None:
    initialize_auth()
    return st.session_state.get(AUTH_USER_KEY)


def get_current_user_id() -> str:
    user = get_current_user()
    if user is None:
        raise RuntimeError("No authenticated user is available.")
    return user.id


def get_access_token() -> str | None:
    initialize_auth()
    return st.session_state.get(AUTH_ACCESS_TOKEN_KEY)


def _store_session(session: AuthSession, *, remember_me: bool = False) -> None:
    from core.navigation import set_active_page, DEFAULT_PAGE
    from core.tenant_session import ensure_tenant_context

    ensure_tenant_context(session.user.id)

    st.session_state[AUTH_USER_KEY] = session.user
    st.session_state[AUTH_ACCESS_TOKEN_KEY] = session.access_token
    st.session_state[AUTH_REFRESH_TOKEN_KEY] = session.refresh_token
    st.session_state[AUTH_BOOTSTRAP_PENDING_KEY] = True
    set_active_page(DEFAULT_PAGE)

    if remember_me:
        from core.auth_persistence import persist_auth_tokens

        persist_auth_tokens(session.access_token, session.refresh_token)

    _start_subscription_trial()
    identify(
        session.user.id,
        traits={"email": session.user.email, "name": session.user.display_name},
    )
    track("user_signed_in", user_id=session.user.id)
    _log_activity(session.user.id, "user.signed_in", "Signed in")


def _log_activity(user_id: str, action: str, message: str) -> None:
    try:
        from services.activity_service import ActivityService

        ActivityService(user_id).log(action, message)
    except Exception:
        pass


def complete_auth_bootstrap() -> None:
    """Load profile and usage records after sign-in."""

    if not st.session_state.pop(AUTH_BOOTSTRAP_PENDING_KEY, False):
        return

    user = get_current_user()
    if user is None:
        return

    from services.user_bootstrap import bootstrap_user_account

    try:
        bootstrap_user_account(user)
    except Exception:
        pass


def is_auth_bootstrap_pending() -> bool:
    return bool(st.session_state.get(AUTH_BOOTSTRAP_PENDING_KEY))


def _start_subscription_trial() -> None:
    from services.usage_service import UsageService

    try:
        UsageService().start_trial()
    except Exception:
        pass


def clear_auth_session() -> None:
    from core.auth_persistence import clear_persisted_tokens
    from core.navigation import PUBLIC_DEFAULT_PAGE, set_active_page
    from core.tenant_session import clear_tenant_session

    user = st.session_state.get(AUTH_USER_KEY)
    access_token = st.session_state.get(AUTH_ACCESS_TOKEN_KEY)
    refresh_token = st.session_state.get(AUTH_REFRESH_TOKEN_KEY)

    try:
        AuthService().sign_out(access_token, refresh_token)
    except AuthError:
        pass

    clear_persisted_tokens()
    clear_tenant_session()

    if user is not None:
        _log_activity(user.id, "user.signed_out", "Signed out")

    st.session_state[AUTH_USER_KEY] = None
    st.session_state[AUTH_ACCESS_TOKEN_KEY] = None
    st.session_state[AUTH_REFRESH_TOKEN_KEY] = None
    st.session_state[AUTH_RECOVERY_MODE_KEY] = False
    st.session_state[AUTH_BOOTSTRAP_PENDING_KEY] = False
    st.session_state[AUTH_REMEMBER_ME_KEY] = False
    st.session_state[AUTH_VIEW_KEY] = "sign_in"
    set_active_page(PUBLIC_DEFAULT_PAGE)


def sign_in(email: str, password: str, *, remember_me: bool = False) -> User:
    session = AuthService().sign_in(email, password)
    st.session_state[AUTH_REMEMBER_ME_KEY] = remember_me
    _store_session(session, remember_me=remember_me)
    return session.user


def sign_up(email: str, password: str, *, full_name: str = "") -> User | None:
    session = AuthService().sign_up(email, password, full_name=full_name)

    if session is None:
        st.session_state[AUTH_PENDING_EMAIL_KEY] = email.strip()
        st.session_state[AUTH_VIEW_KEY] = "verify_email"
        track("user_signed_up_pending_verification", properties={"email": email.strip()})
        return None

    _store_session(session, remember_me=True)
    track("user_signed_up", user_id=session.user.id)
    return session.user


def sign_out() -> None:
    clear_auth_session()


def auth_is_configured() -> bool:
    return is_supabase_configured() or AUTH_DEV_BYPASS


def is_admin() -> bool:
    """Return True when the signed-in user has platform admin access."""

    user = get_current_user()
    if user is None:
        return False

    if user.id in config.ADMIN_USER_IDS:
        return True

    if user.email and user.email.lower() in {email.lower() for email in config.ADMIN_EMAILS}:
        return True

    try:
        from services.profile_service import ProfileService

        return ProfileService(user.id).get_role() == "admin"
    except Exception:
        return False


def render_auth_gate() -> None:
    from ui.auth import render_auth_page

    render_auth_page()
