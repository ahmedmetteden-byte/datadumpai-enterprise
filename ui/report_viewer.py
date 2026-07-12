"""
DataDumpAI v1.0
Report Viewer
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.workspace_navigation import set_workspace_section
from services.export_service import ExportService
from services.report_service import ReportService
from ui.projects import get_current_project
from ui.report_downloads import render_premium_downloads
from ui.report_renderer import render_report_content

export_service = ExportService()
report_service = ReportService()


def _format_created(value: str) -> str:
    if not value:
        return "—"

    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y · %H:%M")
    except (TypeError, ValueError):
        return value[:19]


def render_report_viewer() -> None:
    """Read a report selected from the library."""

    report = st.session_state.get("selected_report")

    if report is None:
        return

    project = get_current_project()

    try:
        report_data = report_service.load_report_data(
            project["id"],
            report.get("filename", ""),
        )
    except (FileNotFoundError, PermissionError):
        st.error("This report file is missing. It may have been deleted.")
        st.session_state.pop("selected_report", None)
        return

    st.divider()

    title_col, close_col = st.columns([6, 1])

    with title_col:
        st.markdown(f"### {report['name']}")

    with close_col:
        if st.button("Close", use_container_width=True, key="close_report_viewer"):
            st.session_state.pop("selected_report", None)
            st.rerun()

    meta1, meta2, meta3 = st.columns(3)

    with meta1:
        st.caption("Created")
        st.write(_format_created(report.get("created_at", "")))

    with meta2:
        st.caption("Project")
        st.write(project["name"])

    with meta3:
        st.caption("Type")
        st.write(report["name"])

    st.markdown("---")
    render_report_content(report_data)
    st.divider()

    render_premium_downloads(
        project_id=project["id"],
        project_name=project["name"],
        report=report_data,
        key_prefix="viewer",
    )

    if st.button("Ask AI about this report", use_container_width=True, key="viewer_ask_copilot"):
        st.session_state.report_for_chat = report
        set_workspace_section("copilot")
        st.rerun()
