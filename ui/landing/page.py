"""
Public marketing landing page.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import APP_NAME, APP_TAGLINE, COMPANY_WEBSITE, PLANS
from core.auth import AUTH_VIEW_KEY
from core.navigation import set_active_page
from ui.usage import render_plan_comparison

WORDMARK_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo.png"

FEATURES = [
    ("📄", "Upload anything", "PDFs, Word, Excel, PowerPoint — drop files and go."),
    ("🤖", "AI reports in minutes", "Board packs, management updates, and executive summaries."),
    ("📊", "Intelligence outputs", "Charts, cross-document insights, and live web research."),
    ("🔒", "Your data, isolated", "Per-user workspaces with optional cloud database and storage."),
]


def render_landing_page() -> None:
    _render_styles()

    if WORDMARK_PATH.exists():
        st.image(str(WORDMARK_PATH), width=280)
    else:
        st.title(APP_NAME)

    st.markdown(
        f"""
<div class="dde-landing-hero">
<h1>Turn documents into board-ready reports</h1>
<p>{APP_TAGLINE}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Get started free", type="primary", use_container_width=True):
            st.session_state[AUTH_VIEW_KEY] = "sign_up"
            set_active_page("auth")
            st.rerun()
    with col2:
        if st.button("Sign in", use_container_width=True):
            st.session_state[AUTH_VIEW_KEY] = "sign_in"
            set_active_page("auth")
            st.rerun()
    with col3:
        st.caption("14-day Professional trial · No credit card required")

    st.divider()

    st.markdown("### Why teams choose DataDumpAI")
    feature_cols = st.columns(len(FEATURES))
    for col, (icon, title, blurb) in zip(feature_cols, FEATURES):
        with col:
            st.markdown(f"#### {icon} {title}")
            st.caption(blurb)

    st.divider()
    st.markdown("### Plans")
    render_plan_comparison()

    st.divider()
    st.markdown("### Ready to save hours every reporting cycle?")
    if st.button("Start your free trial", type="primary"):
        st.session_state[AUTH_VIEW_KEY] = "sign_up"
        set_active_page("auth")
        st.rerun()

    st.caption(f"Learn more at [{COMPANY_WEBSITE}]({COMPANY_WEBSITE})")


def _render_styles() -> None:
    st.markdown(
        """
<style>
.dde-landing-hero h1 {
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
}
.dde-landing-hero p {
    color: #64748b;
    font-size: 1.1rem;
}
</style>
""",
        unsafe_allow_html=True,
    )
