"""
DataDumpAI
Project Workspace Shell
"""

from __future__ import annotations

import inspect
import logging
import streamlit as st

from core.workspace_navigation import get_workspace_section
from ui.hero import render_hero
from ui.onboarding import render_onboarding_wizard
from ui.project_summary import render_project_summary
from ui.report_preview import render_report_preview_if_open
from ui.report_session_trace import log_report_session_state

logger = logging.getLogger(__name__)


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
    if section_id == "account":
        from ui.workspace.sections import account as section

        return section.render
    return None


def render_workspace_shell() -> None:
    """Render the active workspace section."""

    active_section = get_workspace_section()
    is_ai_workspace = active_section == "documents"
    log_report_session_state(f"workspace_shell_enter section={active_section}")

    if not is_ai_workspace:
        render_hero()
        render_onboarding_wizard()
        render_project_summary()

    if active_section == "overview":
        renderer = _section_renderer("overview")
        if renderer:
            renderer()
        render_report_preview_if_open()
        return

    if not is_ai_workspace:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    renderer = _section_renderer(active_section)

    if renderer:
        renderer_module = inspect.getmodule(renderer)
        module_path = getattr(renderer_module, "__file__", renderer.__module__)
        logger.info(
            "Workspace section %r rendered by %s (%s)",
            active_section,
            renderer.__module__,
            module_path,
        )
        renderer()
    else:
        st.info("This section is not available.")

    render_report_preview_if_open()
