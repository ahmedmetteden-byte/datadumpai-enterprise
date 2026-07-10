"""
Authentication form components.
"""

from __future__ import annotations

import streamlit as st

from core.auth import (
    AUTH_PENDING_EMAIL_KEY,
    AUTH_RECOVERY_MODE_KEY,
    AUTH_VIEW_KEY,
    get_access_token,
    sign_in,
    sign_out,
    sign_up,
)
from services.auth_service import AuthError, AuthService
from ui.feedback import show_error, show_success


def render_sign_in_form() -> None:
    st.markdown('<div class="dde-auth-card">', unsafe_allow_html=True)
    st.markdown("### Sign in")

    with st.form("sign_in_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        remember_me = st.checkbox("Remember me", value=True)

        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Enter your email and password.")
        else:
            try:
                sign_in(email, password, remember_me=remember_me)
                st.rerun()
            except AuthError as exc:
                if "verify your email" in str(exc).lower():
                    st.session_state[AUTH_PENDING_EMAIL_KEY] = email.strip()
                    st.session_state[AUTH_VIEW_KEY] = "verify_email"
                    st.rerun()
                show_error(exc)

    if st.button("Forgot password?", use_container_width=True):
        st.session_state[AUTH_VIEW_KEY] = "forgot_password"
        st.rerun()

    st.markdown(
        '<p class="dde-auth-switch">Don\'t have an account?</p>',
        unsafe_allow_html=True,
    )

    if st.button("Create account", use_container_width=True):
        st.session_state[AUTH_VIEW_KEY] = "sign_up"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_sign_up_form() -> None:
    st.markdown('<div class="dde-auth-card">', unsafe_allow_html=True)
    st.markdown("### Create your account")

    with st.form("sign_up_form"):
        full_name = st.text_input("Full name", placeholder="Ada Lovelace")
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")

        submitted = st.form_submit_button(
            "Create account",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not email.strip() or not password:
            st.warning("Enter your email and password.")
        elif password != confirm_password:
            st.warning("Passwords do not match.")
        elif len(password) < 8:
            st.warning("Password must be at least 8 characters.")
        else:
            try:
                user = sign_up(email, password, full_name=full_name)
                if user is not None:
                    show_success("Welcome to DataDumpAI.")
                    st.rerun()
                else:
                    st.rerun()
            except AuthError as exc:
                show_error(exc)

    st.markdown(
        '<p class="dde-auth-switch">Already have an account?</p>',
        unsafe_allow_html=True,
    )

    if st.button("Back to sign in", use_container_width=True):
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_forgot_password_form() -> None:
    st.markdown('<div class="dde-auth-card">', unsafe_allow_html=True)
    st.markdown("### Reset your password")
    st.caption("We will email you a secure link to choose a new password.")

    with st.form("forgot_password_form"):
        email = st.text_input("Email", placeholder="you@company.com")
        submitted = st.form_submit_button(
            "Send reset link",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not email.strip():
            st.warning("Enter your email address.")
        else:
            try:
                AuthService().send_password_reset(email)
                show_success(
                    "If an account exists for that email, a reset link is on its way."
                )
            except AuthError as exc:
                show_error(exc)

    if st.button("Back to sign in", use_container_width=True):
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_reset_password_form() -> None:
    st.markdown('<div class="dde-auth-card">', unsafe_allow_html=True)
    st.markdown("### Choose a new password")

    with st.form("reset_password_form"):
        password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button(
            "Update password",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not password:
            st.warning("Enter a new password.")
        elif password != confirm_password:
            st.warning("Passwords do not match.")
        elif len(password) < 8:
            st.warning("Password must be at least 8 characters.")
        else:
            access_token = get_access_token()
            refresh_token = st.session_state.get("auth_refresh_token")

            if not access_token or not refresh_token:
                st.warning("Your reset session has expired. Request a new link.")
            else:
                try:
                    AuthService().update_password(
                        password,
                        access_token,
                        refresh_token,
                    )
                    st.session_state[AUTH_RECOVERY_MODE_KEY] = False
                    st.session_state[AUTH_VIEW_KEY] = "sign_in"
                    sign_out()
                    show_success("Password updated. Sign in with your new password.")
                    st.rerun()
                except AuthError as exc:
                    show_error(exc)

    st.markdown("</div>", unsafe_allow_html=True)


def render_verify_email_notice() -> None:
    st.markdown('<div class="dde-auth-card">', unsafe_allow_html=True)
    st.markdown("### Verify your email")

    pending_email = st.session_state.get(AUTH_PENDING_EMAIL_KEY, "your inbox")
    st.info(
        f"We sent a verification link to **{pending_email}**. "
        "Open it to activate your account, then sign in."
    )

    if st.button("Resend verification email", type="primary", use_container_width=True):
        try:
            AuthService().resend_verification(pending_email)
            show_success("Verification email sent.")
        except AuthError as exc:
            show_error(exc)

    if st.button("Back to sign in", use_container_width=True):
        st.session_state[AUTH_VIEW_KEY] = "sign_in"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_change_password_form() -> None:
    st.markdown("### Change password")

    with st.form("change_password_form"):
        current_password = st.text_input("Current password", type="password")
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button(
            "Update password",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not current_password or not new_password:
            st.warning("Enter your current and new passwords.")
        elif new_password != confirm_password:
            st.warning("New passwords do not match.")
        elif len(new_password) < 8:
            st.warning("Password must be at least 8 characters.")
        else:
            access_token = get_access_token()
            refresh_token = st.session_state.get("auth_refresh_token")
            email = st.session_state.get("auth_user").email if st.session_state.get("auth_user") else ""

            if not access_token or not refresh_token or not email:
                st.warning("Your session has expired. Sign in again.")
            else:
                try:
                    session = AuthService().sign_in(email, current_password)
                    AuthService().update_password(
                        new_password,
                        session.access_token,
                        session.refresh_token,
                    )
                    from core.auth import _store_session

                    _store_session(session, remember_me=st.session_state.get("auth_remember_me", False))
                    show_success("Password updated.")
                except AuthError as exc:
                    show_error(exc)
