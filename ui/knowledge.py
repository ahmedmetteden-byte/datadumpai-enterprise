"""
DataDumpAI Enterprise
Enterprise Knowledge UI

A window into the Knowledge Store —
not the store itself.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.workspace import Workspace
from models.knowledge import KnowledgeStore
from ui.projects import get_current_project


def _format_timestamp(value: str) -> str:
    if not value:
        return "—"

    try:
        timestamp = datetime.fromisoformat(value)
        return timestamp.strftime("%d %b %Y · %H:%M")
    except (TypeError, ValueError):
        return value[:16]


def render_knowledge_summary(store: KnowledgeStore) -> None:
    """Display Knowledge Store coverage metrics."""

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Sources", store.source_count)
    c2.metric("Documents", store.document_count)
    c3.metric("Reports", store.report_count)
    c4.metric("Exports", store.export_count)
    c5.metric(
        "Meetings",
        store.meeting_count,
    )


def render_knowledge_entries(store: KnowledgeStore) -> None:
    """Display every indexed knowledge entry."""

    st.subheader("Knowledge Corpus")

    if not store.entries:

        st.info(
            "No knowledge indexed yet. Upload documents or generate "
            "reports to build the Knowledge Store."
        )

        return

    for entry in store.entries:

        icon_col, body_col = st.columns([1, 12])

        with icon_col:
            st.markdown(f"### {entry.icon}")

        with body_col:
            st.markdown(f"**{entry.title}**")
            st.caption(
                f"{entry.source_type.title()} · "
                f"{_format_timestamp(entry.created_at)}"
            )

            if entry.summary:
                st.write(entry.summary)

        st.divider()


def render_knowledge() -> None:
    """
    Enterprise Knowledge — searchable corpus of this Workspace.
    """

    workspace = Workspace(
        get_current_project()["id"]
    )

    store = workspace.knowledge

    st.markdown("## Enterprise Knowledge")

    st.caption(
        "Every document, report, export, and activity becomes part of "
        "one searchable Knowledge Store — the foundation for Search, "
        "AI, and Executive Intelligence."
    )

    if store.ready:
        st.success(
            f"Knowledge Store ready · {store.source_count} sources indexed"
        )
    else:
        st.warning("Knowledge Store is empty for this workspace.")

    render_knowledge_summary(store)

    st.divider()

    render_knowledge_entries(store)
