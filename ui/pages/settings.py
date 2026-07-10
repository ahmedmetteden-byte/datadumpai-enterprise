"""
DataDumpAI Enterprise
Settings Page
"""

from __future__ import annotations

from core.navigation import set_active_page
from core.workspace_navigation import set_workspace_section
from ui.workspace.sections.settings import render as render_settings_section


def render() -> None:
    set_active_page("workspace")
    set_workspace_section("settings")
    render_settings_section()
