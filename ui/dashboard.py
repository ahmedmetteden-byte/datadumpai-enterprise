"""
DataDumpAI Enterprise
Dashboard Module
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from core.workspace import Workspace
from ui.projects import get_current_project
from ui.search import render_enterprise_search


def _format_storage(size_bytes: int) -> str:
    """Format storage size for display."""

    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"

    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_timestamp(value: str) -> str:
    """Format an ISO timestamp for display."""

    if not value:
        return "—"

    try:
        timestamp = datetime.fromisoformat(value)

        return timestamp.strftime("%d %b %Y")

    except (TypeError, ValueError):
        return value[:10]


def _file_icon(filename: str) -> str:
    """Return an icon for a document based on its extension."""

    icons = {
        ".pdf": "📕",
        ".docx": "📄",
        ".doc": "📄",
        ".xlsx": "📊",
        ".xls": "📊",
        ".csv": "📊",
        ".pptx": "📽️",
        ".txt": "📝",
    }

    return icons.get(Path(filename).suffix.lower(), "📎")


def render_recent_documents(workspace: Workspace) -> None:
    """Display recent documents from the workspace."""

    st.subheader("Recent Documents")

    if not workspace.recent_documents:

        st.caption("No documents stored yet.")

        return

    for document in workspace.recent_documents:

        name_col, date_col, size_col = st.columns([4, 2, 1])

        icon = _file_icon(document["filename"])

        with name_col:
            st.write(f"{icon} {document['filename']}")

        with date_col:
            st.write(
                _format_timestamp(
                    document.get("uploaded_at", "")
                )
            )

        with size_col:
            st.write(
                _format_storage(document["size"])
            )


def render_recent_reports(workspace: Workspace) -> None:
    """Display recent reports from the workspace."""

    st.subheader("Recent Reports")

    if not workspace.recent_reports:

        st.caption("No reports have been generated yet.")

        return

    for index, report in enumerate(workspace.recent_reports):

        name_col, open_col = st.columns([5, 1])

        with name_col:
            st.write(f"📑 {report['name']}")

        with open_col:
            if st.button(
                "Open →",
                key=f"recent_report_{report['filename']}_{index}",
            ):
                st.session_state.selected_report = report
                from core.workspace_navigation import set_workspace_section

                set_workspace_section("reports")
                st.rerun()


def render_workspace_health(workspace: Workspace) -> None:
    """Display instant workspace health guidance."""

    st.subheader("Workspace Health")

    st.caption(
        "Instant assessment of what is complete and what still needs attention."
    )

    for indicator in workspace.health:
        st.markdown(
            f"{indicator.icon} {indicator.message}"
        )


def render_project_statistics(workspace: Workspace) -> None:
    """Display live workspace statistics."""

    documents_col, reports_col, exports_col, storage_col, activity_col = st.columns(5)

    with documents_col:
        st.metric(
            "Documents",
            workspace.document_count,
        )

    with reports_col:
        st.metric(
            "Reports",
            workspace.report_count,
        )

    with exports_col:
        st.metric(
            "Exports",
            workspace.export_count,
        )

    with storage_col:
        st.metric(
            "Storage Used",
            _format_storage(workspace.storage),
        )

    with activity_col:
        st.metric(
            "Last Activity",
            _format_timestamp(workspace.last_activity),
        )

    st.caption(f"AI: {workspace.ai.status}")

    render_workspace_health(workspace)

    render_recent_documents(workspace)

    render_recent_reports(workspace)


def render_overview() -> None:
    """Project workspace overview — metrics, health, and recent activity."""

    workspace = Workspace(
        get_current_project()["id"]
    )

    st.markdown("## Overview")

    st.caption(workspace.name)

    from services.usage_service import UsageService

    usage = UsageService().get_snapshot()
    u1, u2, u3 = st.columns(3)
    u1.metric("Plan", usage.plan.title())
    u2.metric("Reports used", f"{usage.reports_used}" + (f" / {usage.reports_limit}" if usage.reports_limit else ""))
    u3.metric("Uploads used", f"{usage.uploads_used}" + (f" / {usage.uploads_limit}" if usage.uploads_limit else ""))

    render_project_statistics(workspace)


def render_analytics() -> None:
    """Project workspace analytics — search and insights."""

    Workspace(
        get_current_project()["id"]
    )

    st.markdown("## Analytics")

    st.caption("Search and explore project knowledge.")

    render_enterprise_search()


def render_dashboard() -> None:
    """
    Executive dashboard and project metrics.
    """

    render_overview()

    st.divider()

    render_analytics()
