"""
DataDumpAI v1.0
Sidebar — project picker and workspace navigation.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import APP_TAGLINE_SHORT
from core.auth import get_current_user, is_admin, sign_out
from core.navigation import get_active_page, set_active_page
from core.workspace_navigation import (
    get_workspace_section,
    get_workspace_sections,
    set_workspace_section,
)
from ui.projects import render_project_manager
from ui.usage import render_usage_meter
from services.notification_service import render_notification_bell

SIDEBAR_LOGO_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "logo.png"
)


def render_sidebar() -> None:
    user = get_current_user()

    with st.sidebar:
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

        for section in get_workspace_sections():
            is_active = section.id == active_section

            if st.button(
                f"{section.icon}  {section.title}",
                key=f"nav_section_{section.id}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                set_workspace_section(section.id)
                st.rerun()

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)

        render_usage_meter(compact=True)
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

        display_name = user.display_name if user else "User"
        if is_admin():
            role = "Admin"
        elif user and user.email_verified:
            role = "Verified"
        else:
            role = "Account"
        initials = user.initials if user else "U"

        st.markdown(
            f"""
<div class="dde-user-card">
<div class="dde-user-avatar">{initials}</div>
<div class="dde-user-meta">
<div class="dde-user-name">{display_name}</div>
<div class="dde-user-role">{role}</div>
</div>
</div>
""",
            unsafe_allow_html=True,
        )

        if st.button("Sign out", use_container_width=True, key="sidebar_sign_out"):
            sign_out()
            st.rerun()
