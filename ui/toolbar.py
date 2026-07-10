"""
DataDumpAI
Top Toolbar
"""

from __future__ import annotations

import streamlit as st

from config import APP_NAME, APP_TAGLINE, APP_VERSION


def render_toolbar() -> None:
    c1, c2 = st.columns([8, 2], gap="large")

    with c1:
        st.markdown(
            f"""
<div class="dde-toolbar">
<span class="dde-toolbar-title">{APP_NAME}</span>
<span class="dde-toolbar-tagline">{APP_TAGLINE}</span>
<span class="dde-toolbar-version">v{APP_VERSION}</span>
</div>
""",
            unsafe_allow_html=True,
        )

    with c2:
        st.button(
            "Send Feedback",
            use_container_width=True,
        )
