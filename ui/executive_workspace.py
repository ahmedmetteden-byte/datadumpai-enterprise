"""
DataDumpAI Enterprise
Executive Workspace
"""

from __future__ import annotations

import streamlit as st

from ui.dashboard import render_project_statistics


def render_executive_workspace() -> None:

    st.markdown("## Executive Workspace")

    tabs = st.tabs(
        [
            "Home",
            "Inbox",
            "Tasks",
            "Approvals",
            "Assignments",
            "Notifications",
            "Activity",
            "Execution",
        ]
    )

    with tabs[0]:

        render_project_statistics()

        st.write("")

        left, right = st.columns([2, 1])

        with left:

            st.subheader("Recent Activity")

            st.dataframe(
                {
                    "Time": [
                        "09:14",
                        "09:42",
                        "10:06",
                        "11:30",
                    ],
                    "Activity": [
                        "Board Report Generated",
                        "Annual Report Uploaded",
                        "AI Summary Completed",
                        "Meeting Recording Indexed",
                    ],
                    "Status": [
                        "Complete",
                        "Indexed",
                        "Ready",
                        "Processing",
                    ],
                },
                use_container_width=True,
                hide_index=True,
            )

        with right:

            st.subheader("Today's Progress")

            st.progress(0.72)

            st.write("72% Daily Target")

            st.write("")

            st.info(
                "4 reports generated today."
            )

            st.success(
                "AI Copilot available."
            )