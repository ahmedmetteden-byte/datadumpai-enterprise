"""
DataDumpAI v1.0
Application Router
"""

from __future__ import annotations

import streamlit as st

from core.navigation import PUBLIC_PAGES, get_active_page, set_active_page
from core.workspace_navigation import (
    initialize_workspace_navigation,
    resolve_workspace_section,
    set_workspace_section,
)
from ui.pages.workspace import render as render_workspace


def render_page() -> None:
    """Render the active application page."""

    initialize_workspace_navigation()

    page = get_active_page()

    if page in PUBLIC_PAGES:
        set_active_page("workspace")
        page = "workspace"

    if page == "admin":
        from core.auth import is_admin

        if not is_admin():
            st.error("You do not have permission to access this page.")
            set_active_page("workspace")
            render_workspace()
            return

        from ui.admin.page import render_admin_page

        render_admin_page()
        return

    if page in {
        "documents",
        "library",
        "document_library",
        "reports",
        "generate",
        "copilot",
        "settings",
        "dashboard",
        "overview",
        "history",
        "knowledge",
        "analytics",
    }:
        section = resolve_workspace_section(page)

        if section:
            set_workspace_section(section)

        set_active_page("workspace")

    if get_active_page() == "workspace":
        render_workspace()
        return

    st.info("This page is under construction.")
