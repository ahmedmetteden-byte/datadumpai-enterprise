"""
DataDumpAI Enterprise
Executive Dashboard
"""

from __future__ import annotations

from core.navigation import set_active_page
from core.workspace_navigation import set_workspace_section
from ui.dashboard import render_dashboard


def render() -> None:
    set_active_page("workspace")
    set_workspace_section("overview")
    render_dashboard()
