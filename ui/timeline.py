"""
DataDumpAI Enterprise
Timeline UI
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.workspace import Workspace


def _format_event_time(timestamp: str) -> str:
    """Format a timeline timestamp for display."""

    if not timestamp:
        return "—"

    try:
        event_time = datetime.fromisoformat(timestamp)

        return event_time.strftime("%H:%M")

    except (TypeError, ValueError):
        return timestamp[:5]


def render_timeline(workspace: Workspace) -> None:
    """Display the project workspace activity timeline."""

    st.subheader("Timeline")

    st.caption(
        f"Activity history for {workspace.name}."
    )

    if not workspace.timeline:

        st.info("No activity recorded yet.")

        return

    for event in workspace.timeline:

        time_col, message_col = st.columns([1, 6])

        with time_col:
            st.markdown(
                f"**{_format_event_time(event.timestamp)}**"
            )

        with message_col:
            st.markdown(event.message)
