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


def _chart_export_error(detail: str) -> str:
    lowered = detail.lower()

    if "chrome" in lowered or "chromium" in lowered:
        return (
            "Chart export requires Chrome for kaleido. "
            "Install dependencies with `pip install -r requirements.txt`, then run "
            "`kaleido_get_chrome` if Chrome is not already available."
        )

    if "kaleido" in lowered:
        return (
            "Chart export requires kaleido v1 with Plotly 6.1 or later. "
            "Run: pip install -r requirements.txt"
        )

    return (
        "Chart export failed. Ensure kaleido v1 is installed and Chrome is available. "
        "Run: pip install -r requirements.txt"
    )


def plotly_figure_to_png(
    figure: go.Figure,
    *,
    width: int = DEFAULT_EXPORT_WIDTH,
    height: int = DEFAULT_EXPORT_HEIGHT,
) -> bytes:
    """Rasterize a Plotly figure for embedding in exported documents."""

    try:
        return figure.to_image(format="png", width=width, height=height, scale=2)
    except Exception as exc:
        detail = str(exc).strip() or type(exc).__name__
        raise RuntimeError(_chart_export_error(detail)) from exc


def render_chart_pngs(chart_data: dict[str, Any]) -> list[tuple[str, bytes]]:
    """Build Plotly figures and render them to PNG bytes for export."""

    return [
        (title, plotly_figure_to_png(figure))
        for title, figure in build_report_chart_figures(chart_data)
    ]
