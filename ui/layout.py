from __future__ import annotations

import streamlit as st


def page_container():
    """
    Main page wrapper.

    Keeps every page aligned to the same width.
    """

    st.markdown(
        """
        <div class="dde-page">
        """,
        unsafe_allow_html=True,
    )


def end_page():
    st.markdown(
        """
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str | None = None):

    st.markdown(
        f"""
        <div class="dde-section">

        <div class="dde-section-title">
            {title}
        </div>

        """,
        unsafe_allow_html=True,
    )

    if subtitle:
        st.markdown(
            f"""
            <div class="dde-section-subtitle">
                {subtitle}
            </div>
            """,
            unsafe_allow_html=True,
        )


def spacer(height: int = 24):
    st.markdown(
        f"<div style='height:{height}px'></div>",
        unsafe_allow_html=True,
    )


def divider():
    st.markdown(
        """
        <div class="dde-divider"></div>
        """,
        unsafe_allow_html=True,
    )