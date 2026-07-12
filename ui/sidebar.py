"""
DataDumpAI v1.0
Sidebar — project picker and workspace navigation.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import APP_TAGLINE_SHORT, PLANS
from core.auth import get_current_user, is_admin, sign_out
from core.navigation import get_active_page, set_active_page
from core.workspace_navigation import (
    get_sidebar_workspace_sections,
    get_workspace_section,
    set_workspace_section,
)
from services.usage_service import UsageService
from ui.projects import render_project_manager
from services.notification_service import render_notification_bell

SIDEBAR_LOGO_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "logo.png"
)


def _open_account_tab(tab_id: str = "profile") -> None:
    st.session_state.account_tab = tab_id
    set_workspace_section("account")


def _render_user_account_panel(user) -> None:
    snapshot = UsageService().get_snapshot()
    plan = PLANS.get(snapshot.plan, PLANS["free"])
    plan_label = plan["label"]

    if snapshot.is_trialing and snapshot.trial_days_remaining is not None:
        plan_subtitle = (
            f"Trial · {snapshot.trial_days_remaining} day"
            f"{'s' if snapshot.trial_days_remaining != 1 else ''} left"
        )
    elif user and user.email_verified:
        plan_subtitle = "Verified"
    else:
        plan_subtitle = "Account"

    display_name = user.display_name if user else "User"

    if st.button(
        f"👤  {display_name}",
        key="sidebar_user_card",
        use_container_width=True,
        help="Open your account and profile",
    ):
        _open_account_tab("profile")
        st.rerun()

    st.caption(f"{plan_label} · {plan_subtitle}")

    sub_col, settings_col = st.columns(2)
    with sub_col:
        if st.button(
            "Subscription",
            use_container_width=True,
            key="sidebar_subscription",
        ):
            _open_account_tab("subscription")
            st.rerun()
    with settings_col:
        if st.button(
            "Settings",
            use_container_width=True,
            key="sidebar_settings",
        ):
            set_workspace_section("settings")
            st.rerun()

    if st.button("Sign out", use_container_width=True, key="sidebar_sign_out"):
        sign_out()
        st.rerun()


def render_sidebar() -> None:
    user = get_current_user()

    with st.sidebar:
        if st.button(
            "Home",
            key="sidebar_logo_home",
            use_container_width=True,
            help="Return to the marketing homepage",
        ):
            set_active_page("landing")
            st.rerun()

        if SIDEBAR_LOGO_PATH.exists():
            st.image(str(SIDEBAR_LOGO_PATH), use_container_width=True)
        else:
            st.markdown("### DataDumpAI")

        st.markdown(
            f'<p class="dde-sidebar-wordmark-tagline">{APP_TAGLINE_SHORT}</p>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        render_project_manager()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.divider()

        st.markdown(
            '<div class="dde-nav-heading">WORKSPACE</div>',
            unsafe_allow_html=True,
        )

        active_section = get_workspace_section()

        for section in get_sidebar_workspace_sections():
            is_active = section.id == active_section

            if st.button(
                f"{section.icon}  {section.title}",
                key=f"nav_section_{section.id}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                set_workspace_section(section.id)
                st.rerun()

            if section.subtitle:
                st.markdown(
                    f'<p class="dde-nav-subtitle{" dde-nav-subtitle-active" if is_active else ""}">'
                    f"{section.subtitle}</p>",
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)

        render_notification_bell()

        if is_admin():
            admin_active = get_active_page() == "admin"
            if st.button(
                "🛡️  Admin",
                use_container_width=True,
                type="primary" if admin_active else "secondary",
                key="nav_admin",
            ):
                set_active_page("admin")
                st.rerun()

        if st.button(
            "💬 Send Feedback",
            use_container_width=True,
            key="sidebar_send_feedback",
        ):
            st.session_state.settings_tab = "feedback"
            set_workspace_section("settings")
            st.rerun()

        st.divider()
        st.markdown(
            '<div class="dde-nav-heading">ACCOUNT</div>',
            unsafe_allow_html=True,
        )

        _render_user_account_panel(user)
