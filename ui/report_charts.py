"""
Plotly charts for executive intelligence reports.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.report_chart_figures import build_report_chart_figures


def render_report_charts(chart_data: dict[str, Any]) -> None:
    """Render bar, pie, and trend charts when chart metadata is present."""

    figures = build_report_chart_figures(chart_data)

    if not figures:
        return

    st.markdown("#### Visual Analytics")

    titles = [title for title, _ in figures]
    has_trends = "Theme Trends" in titles
    columns = st.columns(3 if has_trends else 2)

    for index, (_, figure) in enumerate(figures):
        column = columns[index] if index < len(columns) else st
        with column:
            st.plotly_chart(figure, use_container_width=True)
