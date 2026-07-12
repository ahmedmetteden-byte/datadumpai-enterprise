"""
Project summary card — context and workflow status for the active workspace.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core.workspace import Workspace
from core.workspace_navigation import navigate_to_ai_workspace, set_workspace_section
from ui.formatting import format_relative_time
from ui.projects import get_active_workspace


def _latest_activity(*timestamps: str | None) -> str | None:
    parsed: list[datetime] = []

    for value in timestamps:
        if not value:
            continue

        try:
            timestamp = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            continue

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        parsed.append(timestamp)

    if not parsed:
        return None

    return max(parsed).isoformat()


def _stats_line(document_count: int, report_count: int) -> str:
    document_label = "document" if document_count == 1 else "documents"
    report_label = "report" if report_count == 1 else "reports"
    return (
        f"{document_count} {document_label} uploaded · "
        f"{report_count} {report_label} generated"
    )


def _primary_action_label(document_count: int) -> str:
    if document_count == 0:
        return "Upload to Dump Box"
    return "Open AI Workspace"


def render_project_summary() -> None:
    """Render the workspace context card at the top of the workspace."""

    active_workspace = get_active_workspace()

    if active_workspace.get("is_pending"):
        st.markdown('<div class="dde-project-summary-wrap">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                """
<div class="dde-project-summary">
<div class="dde-project-summary-label">Workspace</div>
<div class="dde-project-summary-name">Project</div>
<div class="dde-project-summary-stats">Create a project to get started</div>
<div class="dde-project-summary-meta">
<span class="dde-project-summary-status">Select Project in the sidebar</span>
</div>
</div>
""",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    workspace = Workspace(active_workspace["id"])

    document_count = workspace.document_count
    report_count = workspace.report_count
    stats_line = _stats_line(document_count, report_count)
    action_label = _primary_action_label(document_count)

    last_activity = _latest_activity(
        active_workspace.get("last_activity"),
        active_workspace.get("updated_at"),
        active_workspace.get("created_at"),
        *(
            document.get("uploaded_at")
            for document in workspace.documents
        ),
        *(
            report.get("created_at")
            for report in workspace.reports
        ),
    )

    activity_text = (
        format_relative_time(last_activity)
        if last_activity
        else "No activity yet"
    )
    label = "Workspace" if active_workspace.get("is_quick_report") else "Project"

    st.markdown('<div class="dde-project-summary-wrap">', unsafe_allow_html=True)

    with st.container(border=True):
        summary_col, action_col = st.columns([3, 1], gap="medium")

        with summary_col:
            st.markdown(
                f"""
<div class="dde-project-summary">
<div class="dde-project-summary-label">{label}</div>
<div class="dde-project-summary-name">{workspace.name}</div>
<div class="dde-project-summary-stats">{stats_line}</div>
<div class="dde-project-summary-meta">
<span><strong>Last activity:</strong> {activity_text}</span>
</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with action_col:
            st.markdown('<div class="dde-summary-actions">', unsafe_allow_html=True)
            if st.button(
                action_label,
                type="primary",
                use_container_width=True,
                key="project_summary_primary_action",
            ):
                if document_count == 0:
                    set_workspace_section("library")
                else:
                    navigate_to_ai_workspace()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
