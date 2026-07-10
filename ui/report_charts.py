"""
Plotly charts for executive intelligence reports.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

CHART_COLORS = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#1D4ED8", "#1E40AF"]


def _chart_layout(**extra: Any) -> dict[str, Any]:
    layout = {
        "margin": dict(l=20, r=20, t=40, b=20),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, sans-serif", "color": "#0F172A"},
        "height": 280,
    }
    layout.update(extra)
    return layout


def render_report_charts(chart_data: dict[str, Any]) -> None:
    """Render bar, pie, and trend charts when chart metadata is present."""

    topics = chart_data.get("topics") or []
    trends = chart_data.get("trends") or []
    risk_distribution = chart_data.get("risk_distribution") or []

    if not topics and not trends and not risk_distribution:
        return

    st.markdown("#### Visual Analytics")

    columns = st.columns(3 if trends else 2)

    column_index = 0

    if topics:
        with columns[column_index]:
            labels = [item.get("label", "") for item in topics]
            values = [float(item.get("value", 0)) for item in topics]

            bar_figure = px.bar(
                x=labels,
                y=values,
                labels={"x": "Theme", "y": "Share (%)"},
                title="Top Discussion Topics",
                color_discrete_sequence=CHART_COLORS,
            )
            bar_figure.update_layout(**_chart_layout())
            bar_figure.update_traces(marker_line_width=0)
            st.plotly_chart(bar_figure, use_container_width=True)

        with columns[column_index + 1]:
            pie_figure = px.pie(
                names=labels,
                values=values,
                title="Theme Distribution",
                color_discrete_sequence=CHART_COLORS,
                hole=0.42,
            )
            pie_figure.update_layout(**_chart_layout())
            st.plotly_chart(pie_figure, use_container_width=True)

        column_index = 2

    if trends:
        trend_column = columns[column_index] if column_index < len(columns) else st

        with trend_column:
            labels = [item.get("label", "") for item in trends]
            prior = [float(item.get("prior", 0)) for item in trends]
            current = [float(item.get("current", 0)) for item in trends]

            trend_figure = go.Figure()
            trend_figure.add_trace(
                go.Scatter(
                    x=labels,
                    y=prior,
                    mode="lines+markers",
                    name="Previous",
                    line={"color": "#94A3B8", "width": 2},
                )
            )
            trend_figure.add_trace(
                go.Scatter(
                    x=labels,
                    y=current,
                    mode="lines+markers",
                    name="Current",
                    line={"color": "#2563EB", "width": 3},
                )
            )
            trend_figure.update_layout(
                **_chart_layout(title="Theme Trends"),
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
            )
            st.plotly_chart(trend_figure, use_container_width=True)

    if risk_distribution and not topics:
        labels = [item.get("label", "") for item in risk_distribution]
        values = [float(item.get("value", 0)) for item in risk_distribution]

        risk_figure = px.bar(
            x=labels,
            y=values,
            title="Risk Distribution",
            color_discrete_sequence=["#DC2626", "#F97316", "#F59E0B"],
        )
        risk_figure.update_layout(**_chart_layout())
        st.plotly_chart(risk_figure, use_container_width=True)
