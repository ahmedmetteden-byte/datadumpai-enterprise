"""
Render shared Plotly chart figures to PNG for PDF and Word export.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from services.report_chart_figures import (
    build_report_chart_figures,
    has_chart_visuals,
    is_visual_summary_heading,
)

DEFAULT_EXPORT_WIDTH = 1200
DEFAULT_EXPORT_HEIGHT = 480


def plotly_figure_to_png(
    figure: go.Figure,
    *,
    width: int = DEFAULT_EXPORT_WIDTH,
    height: int = DEFAULT_EXPORT_HEIGHT,
) -> bytes:
    """Rasterize a Plotly figure for embedding in exported documents."""

    try:
        return figure.to_image(format="png", width=width, height=height, scale=2)
    except Exception as first_error:
        try:
            return figure.to_image(
                format="png",
                width=width,
                height=height,
                scale=2,
                engine="kaleido",
            )
        except Exception as second_error:
            raise RuntimeError(
                "Chart export requires the kaleido package. "
                "Run: pip install kaleido"
            ) from second_error


def render_chart_pngs(chart_data: dict[str, Any]) -> list[tuple[str, bytes]]:
    """Build Plotly figures and render them to PNG bytes for export."""

    return [
        (title, plotly_figure_to_png(figure))
        for title, figure in build_report_chart_figures(chart_data)
    ]
