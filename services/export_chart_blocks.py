"""
Shared helpers for inserting chart images into export render flows.
"""

from __future__ import annotations

from typing import Any

from services.report_chart_export import ChartExportResult, render_chart_pngs
from services.report_chart_figures import has_chart_visuals


def get_export_chart_images(chart_data: dict[str, Any]) -> ChartExportResult:
    """Return titled PNG chart images when report metadata includes chart data."""

    if not has_chart_visuals(chart_data):
        return ChartExportResult(images=[])

    return render_chart_pngs(chart_data)
