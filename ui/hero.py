"""
DataDumpAI
Hero Banner
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import APP_NAME, APP_TAGLINE, APP_TAGLINE_SHORT

HERO_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "datadump-hero-logo.png"


def render_hero_compact() -> None:
    """Minimal header for AI-first workspace — prompt is the hero."""

    st.markdown(
        f"""
<div class="dde-hero-compact">
<div class="dde-hero-compact-name">{APP_NAME}</div>
<div class="dde-hero-compact-tagline">{APP_TAGLINE_SHORT}</div>
<hr class="dde-hero-compact-rule" />
</div>
""",
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
<style>
div[data-testid="stHorizontalBlock"]:has(.dde-hero-marker) {
    background: linear-gradient(135deg, #2340C8, #2563EB, #14B8D4);
    border-radius: 8px;
    padding: 0.55cm 0.7cm;
    margin: 0 0 1rem 0;
    box-shadow: 0 3px 10px rgba(37, 99, 235, 0.14);
    min-height: 5.5cm;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(.dde-hero-marker) [data-testid="stImage"] img {
    background: #ffffff;
    padding: 10px 18px;
    border-radius: 8px;
    max-height: 2.6cm;
    width: auto;
}
.dde-hero-text .dde-hero-subtitle {
    color: #ffffff;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.35;
    margin: 0 0 0.2cm 0;
}
.dde-hero-text .dde-hero-pipeline {
    color: rgba(255, 255, 255, 0.92);
    font-size: 12px;
    line-height: 1.4;
    margin: 0;
}
</style>
""",
        unsafe_allow_html=True,
    )

    logo_col, text_col = st.columns([1.15, 2], gap="medium", vertical_alignment="center")

    with logo_col:
        st.markdown('<div class="dde-hero-marker" style="display:none"></div>', unsafe_allow_html=True)
        if HERO_LOGO_PATH.exists():
            st.image(str(HERO_LOGO_PATH), width=300)

    with text_col:
        st.markdown(
            f"""
<div class="dde-hero-text">
<div class="dde-hero-subtitle">{APP_TAGLINE}</div>
<div class="dde-hero-pipeline">
Upload documents · Generate reports · Download and share
</div>
</div>
""",
            unsafe_allow_html=True,
        )
