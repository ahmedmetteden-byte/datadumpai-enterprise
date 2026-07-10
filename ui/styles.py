"""
DataDumpAI Enterprise
Global stylesheet loader.
"""

from pathlib import Path

import streamlit as st

from core.theme import COLORS, TYPE


def load_styles() -> None:
    """
    Load the application's global stylesheet.
    """

    css_path = Path(__file__).parent.parent / "assets" / "styles.css"

    css = css_path.read_text(encoding="utf-8")

    css = (
        css.replace("__FONT__", TYPE.FONT)
           .replace("__CANVAS__", COLORS.CANVAS)
           .replace("__SURFACE__", COLORS.SURFACE)
           .replace("__SURFACE_ALT__", COLORS.SURFACE_ALT)
           .replace("__SIDEBAR__", COLORS.SIDEBAR)
           .replace("__SIDEBAR_HOVER__", COLORS.SIDEBAR_HOVER)
           .replace("__SIDEBAR_ACTIVE__", COLORS.SIDEBAR_ACTIVE)
           .replace("__TEXT__", COLORS.TEXT)
           .replace("__MUTED__", COLORS.MUTED)
           .replace("__LIGHT__", COLORS.LIGHT)
           .replace("__BORDER__", COLORS.BORDER)
    )

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )