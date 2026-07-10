"""
DataDumpAI
Project Workspace Shell
"""

from __future__ import annotations

import streamlit as st

from core.workspace_navigation import get_workspace_section
from ui.hero import render_hero
from ui.project_summary import render_project_summary
from ui.recent_reports import render_recent_reports
from ui.report_preview import render_report_preview_if_open
from ui.report_viewer import render_report_viewer
from ui.onboarding import render_onboarding_banner, render_onboarding_wizard


def _section_renderer(section_id: str):
    """Import workspace sections lazily — auth may not exist at import time."""

    if section_id == "overview":
        from ui.workspace.sections import overview as section

        return section.render
    if section_id == "documents":
        from ui.workspace.sections import documents as section

        return section.render
    if section_id == "library":
        from ui.workspace.sections import library as section

        return section.render
    if section_id == "reports":
        from ui.workspace.sections import reports as section

        return section.render
    if section_id == "copilot":
        from ui.workspace.sections import copilot as section

        return section.render
    if section_id == "settings":
        from ui.workspace.sections import settings as section

        return section.render
    return None


def render_workspace_shell() -> None:
    """Render the active workspace section."""

    active_section = get_workspace_section()

    render_hero()

    showing_onboarding = render_onboarding_wizard()
    if not showing_onboarding:
        render_onboarding_banner()

    render_project_summary()

    if active_section == "overview":
        renderer = _section_renderer("overview")
        if renderer:
            renderer()
        render_report_preview_if_open()
        return

    if active_section == "documents":
        render_recent_reports()

        if st.session_state.get("selected_report"):
            render_report_viewer()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    renderer = _section_renderer(active_section)

    if renderer:
        renderer()
    else:
        st.info("This section is not available.")

    render_report_preview_if_open()
