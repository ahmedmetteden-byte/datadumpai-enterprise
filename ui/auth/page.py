"""
Authentication page router.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import APP_NAME, APP_TAGLINE, AUTH_DEV_BYPASS, DEBUG, is_supabase_configured
from core.auth import (
    AUTH_RECOVERY_MODE_KEY,
    AUTH_VIEW_KEY,
    auth_is_configured,
    is_authenticated,
)
from ui.auth.forms import (
    render_change_password_form,
    render_forgot_password_form,
    render_reset_password_form,
    render_sign_in_form,
    render_sign_up_form,
    render_verify_email_notice,
)

WORDMARK_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo.png"


def render_auth_page() -> None:
    """Render the public authentication experience."""

    if is_authenticated():
        return

    _render_auth_styles()

    left, center, right = st.columns([1, 1.2, 1])

    with center:
        if WORDMARK_PATH.exists():
            st.image(str(WORDMARK_PATH), use_container_width=True)
        else:
            st.markdown(f"## {APP_NAME}")

        st.markdown(
            f'<p class="dde-auth-tagline">{APP_TAGLINE}</p>',
            unsafe_allow_html=True,
        )

        if AUTH_DEV_BYPASS and not is_supabase_configured() and DEBUG:
            st.info(
                "Development mode: authentication bypass is enabled. "
                "Sign in with any email and password."
            )

        if not auth_is_configured():
            st.error(
                "Authentication is not configured. Add `SUPABASE_URL` and "
                "`SUPABASE_ANON_KEY` to your `.env` file, or set "
                "`AUTH_DEV_BYPASS=true` for local development only."
            )
            return

        auth_success = st.session_state.pop("auth_success", None)
        if auth_success:
            st.success(auth_success)

        auth_error = st.session_state.pop("auth_error", None)
        if auth_error:
            st.error(auth_error)

        if st.session_state.get(AUTH_RECOVERY_MODE_KEY):
            render_reset_password_form()
            return

        view = st.session_state.get(AUTH_VIEW_KEY, "sign_in")

        if view == "sign_up":
            render_sign_up_form()
        elif view == "forgot_password":
            render_forgot_password_form()
        elif view == "verify_email":
            render_verify_email_notice()
        elif view == "reset_password":
            render_reset_password_form()
        elif view == "change_password":
            render_change_password_form()
        else:
            render_sign_in_form()


def _render_auth_styles() -> None:
    st.markdown(
        """
<style>
.dde-auth-tagline {
    color: #64748b;
    margin-top: -0.5rem;
    margin-bottom: 1.5rem;
}
.dde-auth-card {
    padding: 0.25rem 0 1rem 0;
}
.dde-auth-switch {
    margin-top: 1rem;
    color: #64748b;
    font-size: 0.95rem;
}

/* Auth buttons — match app primary blue */
.block-container:has(.dde-auth-card) .stButton > button,
.block-container:has(.dde-auth-card) [data-testid="stFormSubmitButton"] > button {
    background: #2563EB !important;
    border: 2px solid #1D4ED8 !important;
    color: #FFFFFF !important;
    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.28) !important;
    min-height: 46px !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
}

.block-container:has(.dde-auth-card) .stButton > button:hover,
.block-container:has(.dde-auth-card) [data-testid="stFormSubmitButton"] > button:hover {
    background: #1D4ED8 !important;
    border-color: #1E40AF !important;
    color: #FFFFFF !important;
}

.block-container:has(.dde-auth-card) .stButton > button p,
.block-container:has(.dde-auth-card) .stButton > button span,
.block-container:has(.dde-auth-card) [data-testid="stFormSubmitButton"] > button p,
.block-container:has(.dde-auth-card) [data-testid="stFormSubmitButton"] > button span {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* Auth fields — clearer borders and labels */
.block-container:has(.dde-auth-card) [data-testid="stTextInput"] label p,
.block-container:has(.dde-auth-card) [data-testid="stTextInput"] label {
    color: #0F172A !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}

.block-container:has(.dde-auth-card) [data-testid="stTextInput"] [data-baseweb="input"] {
    background: #FFFFFF !important;
    border: 2px solid #94A3B8 !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
}

.block-container:has(.dde-auth-card) [data-testid="stTextInput"] input {
    background: #FFFFFF !important;
    color: #0F172A !important;
    border: 2px solid #94A3B8 !important;
    border-radius: 10px !important;
    min-height: 46px !important;
    padding: 0.65rem 0.85rem !important;
    font-size: 1rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
}

.block-container:has(.dde-auth-card) [data-testid="stTextInput"] input:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
    outline: none !important;
}

.block-container:has(.dde-auth-card) [data-testid="stTextInput"] input::placeholder {
    color: #64748B !important;
    opacity: 1 !important;
}

.block-container:has(.dde-auth-card) [data-testid="stCheckbox"] label p {
    color: #334155 !important;
    font-weight: 500 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
