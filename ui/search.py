"""
DataDumpAI Enterprise
Enterprise Search Module
"""

from __future__ import annotations

import streamlit as st

from application.search_pipeline import SearchPipeline
from core.workspace import Workspace
from ui.projects import get_current_project

search_pipeline = SearchPipeline()


def render_enterprise_search(*, scope_project: bool = True) -> None:
    """
    Render the organization-wide enterprise search box and results.
    """

    workspace = Workspace(
        get_current_project()["id"]
    )

    st.markdown("### Search")

    query = st.text_input(
        "Search",
        placeholder="Search documents, reports, and projects...",
        label_visibility="collapsed",
    )

    if not query.strip():
        return

    project_id = None

    if scope_project:
        project_id = workspace.project_id

    results = search_pipeline.search(
        query,
        project_id=project_id,
    )

    if not results:

        st.caption("No results found.")

        return

    st.markdown("---")

    for result in results:

        st.markdown(f"**{result.title}**")
        st.caption(result.location)

        if result.project_name and not scope_project:
            st.caption(f"Project: {result.project_name}")

        if result.excerpt:
            st.write(result.excerpt)

        st.markdown("---")
