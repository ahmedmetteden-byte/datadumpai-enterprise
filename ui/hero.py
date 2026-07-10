"""
DataDumpAI
Hero Banner
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

from config import APP_TAGLINE

HERO_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "datadump-hero-logo.png"


@lru_cache(maxsize=1)
def _hero_logo_data_uri() -> str:
    encoded = base64.b64encode(HERO_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_hero() -> None:
    logo_markup = ""

    if HERO_LOGO_PATH.exists():
        logo_markup = (
            f'<img class="dde-hero-logo-image" '
            f'src="{_hero_logo_data_uri()}" alt="DataDumpAI" />'
        )

    st.markdown(
        f"""
<div class="dde-hero">
<div class="dde-hero-main">
{logo_markup}
<div class="dde-hero-details">
<div class="dde-hero-subtitle">
{APP_TAGLINE}
</div>
<div class="dde-hero-pipeline">
Upload documents · Generate reports · Download and share
</div>
</div>
</div>
</div>
""",
        unsafe_allow_html=True,
    )
