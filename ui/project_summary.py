"""
Project summary card — context and workflow status for the active workspace.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core.workspace import Workspace
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


def _status_message(document_count: int, report_count: int) -> str:
    if document_count == 0:
        return "Upload documents to get started"

    if report_count == 0:
        return "Ready to generate reports"

    return "Ready to generate more reports"


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
    document_label = "document" if document_count == 1 else "documents"
    report_label = "report" if report_count == 1 else "reports"

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
    status = _status_message(document_count, report_count)
    label = "Workspace" if active_workspace.get("is_quick_report") else "Project"

    st.markdown('<div class="dde-project-summary-wrap">', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            f"""
<div class="dde-project-summary">
<div class="dde-project-summary-label">{label}</div>
<div class="dde-project-summary-name">{workspace.name}</div>
<div class="dde-project-summary-stats">
{document_count} {document_label} · {report_count} {report_label}
</div>
<div class="dde-project-summary-meta">
<span><strong>Last activity:</strong> {activity_text}</span>
<span class="dde-project-summary-status">{status}</span>
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
