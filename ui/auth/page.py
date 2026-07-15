"""
Authentication page router.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import APP_NAME, APP_TAGLINE
from core.auth import (
    AUTH_RECOVERY_MODE_KEY,
    AUTH_VIEW_KEY,
    auth_is_configured,
    is_authenticated,
)
from core.auth_callbacks import recovery_failed
from ui.auth.forms import (
    render_change_password_form,
    render_forgot_password_form,
    render_reset_password_form,
    render_sign_in_form,
    render_sign_up_form,
    render_verify_email_notice,
)

WORDMARK_PATH = Path(__file__).resolve().parents[2] / "assets" / "auth-wordmark.png"


def render_auth_page() -> None:
    """Render the public authentication experience."""

    from core.recovery_callback_trace import explain_sign_in_render, log_recovery_trace

    if is_authenticated():
        log_recovery_trace("auth_page.exit", reason="is_authenticated_true")
        return

    log_recovery_trace("auth_page.render", **explain_sign_in_render())

    _render_auth_styles()

    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.markdown('<div class="dde-auth-wordmark-marker" style="display:none"></div>', unsafe_allow_html=True)
        if WORDMARK_PATH.exists():
            st.image(str(WORDMARK_PATH), width=320)
        else:
            st.markdown(f"## {APP_NAME}")

        st.markdown(
            f'<p class="dde-auth-tagline">{APP_TAGLINE}</p>',
            unsafe_allow_html=True,
        )

        if not auth_is_configured():
            st.error(
                "Authentication is not configured. Add `SUPABASE_URL` and "
                "`SUPABASE_ANON_KEY` to your `.env` file to enable "
                "multi-user sign-in."
            )
            return

        auth_success = st.session_state.pop("auth_success", None)
        if auth_success:
            st.success(auth_success)

        auth_error = st.session_state.pop("auth_error", None)
        if auth_error and "too many verification emails" not in str(auth_error).lower():
            st.error(auth_error)

        if recovery_failed():
            if st.button(
                "Request a new password reset email",
                type="primary",
                use_container_width=True,
                key="auth_recovery_request_new_link",
            ):
                st.session_state[AUTH_VIEW_KEY] = "forgot_password"
                st.session_state.pop("auth_recovery_failed", None)
                st.rerun()

        if st.session_state.get(AUTH_RECOVERY_MODE_KEY):
            log_recovery_trace("auth_page.view", view="reset_password_form")
            render_reset_password_form()
            return

        view = st.session_state.get(AUTH_VIEW_KEY, "sign_in")
        log_recovery_trace("auth_page.view", view=view)

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
.block-container:has(.dde-auth-wordmark-marker) [data-testid="stImage"] {
    display: flex;
    justify-content: center;
}
.block-container:has(.dde-auth-wordmark-marker) [data-testid="stImage"] img {
    width: 320px;
    max-width: 100%;
    height: auto;
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
