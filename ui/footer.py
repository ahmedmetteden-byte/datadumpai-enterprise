"""
Application footer — version and release information.
"""

from __future__ import annotations

import streamlit as st

from config import APP_RELEASE_LABEL, APP_VERSION


def render_app_footer() -> None:
    """Render the global page footer."""

    st.markdown(
        f"""
<div class="dde-app-footer">
<div class="dde-app-footer-version">Version {APP_VERSION}</div>
<div class="dde-app-footer-release">{APP_RELEASE_LABEL}</div>
</div>
""",
        unsafe_allow_html=True,
    )
