"""
Project Workspace — Documents (upload and report generation)
"""

from __future__ import annotations

import streamlit as st

from ui.document_library import render_document_upload
from ui.projects import (
    get_active_workspace,
    get_user_projects,
    initialize_projects,
    is_project_pending,
)
from ui.report_generation import (
    render_document_source_selection,
    render_documents_page_generation,
)


def render() -> None:
    initialize_projects()
    workspace = get_active_workspace()
    user_projects = get_user_projects()

    if workspace.get("is_pending"):
        st.markdown("## Documents")
        st.info(
            "Select **Project** in the sidebar and create your project to start "
            "uploading documents."
        )
        return

    if workspace.get("is_quick_report"):
        st.markdown("## Documents")
        st.caption(
            "You are in **Quick Report**. Uploads here stay outside any project. "
            "Select **Project** in the sidebar for an isolated workspace."
        )
    else:
        st.markdown("## Documents")
        st.caption(
            f"Uploads and generated reports stay inside **{workspace['name']}**. "
            "Switch to **Quick Report** in the sidebar to upload without a project."
        )

    render_document_upload()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    document_selection = render_document_source_selection(user_projects, workspace)

    st.markdown("---")
    render_documents_page_generation(user_projects, document_selection)
