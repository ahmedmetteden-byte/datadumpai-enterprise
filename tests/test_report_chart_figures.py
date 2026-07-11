"""Tests for the shared Plotly chart figure pipeline."""

from __future__ import annotations

import pytest

from services.report_chart_data import extract_chart_data, prepare_report_for_output
from services.report_chart_export import is_chart_export_available, render_chart_pngs
from services.report_chart_figures import build_report_chart_figures

SAMPLE_CHART_DATA = {
    "topics": [{"label": "Claims", "value": 31}, {"label": "Capital", "value": 21}],
    "trends": [{"label": "Claims", "prior": 15, "current": 31}],
    "health_score": 75,
}


def test_build_report_chart_figures_matches_browser_chart_set():
    figures = build_report_chart_figures(SAMPLE_CHART_DATA)

    assert [title for title, _ in figures] == [
        "Top Discussion Topics",
        "Theme Distribution",
        "Theme Trends",
    ]


def test_render_chart_pngs_uses_same_figure_pipeline_as_browser():
    is_chart_export_available.cache_clear()
    if not is_chart_export_available():
        pytest.skip("Chart export runtime is not available in this environment")

    figures = build_report_chart_figures(SAMPLE_CHART_DATA)
    result = render_chart_pngs(SAMPLE_CHART_DATA)

    assert len(figures) == len(result.images)
    assert result.images[0][0] == figures[0][0]
    assert result.images[0][1].startswith(b"\x89PNG")


def test_prepare_report_for_output_keeps_chart_data_for_export():
    report = (
        "## Full Report Overview\n\n"
        '<!-- REPORT_CHARTS\n'
        '{"topics": [{"label": "Claims", "value": 31}], "health_score": 75}\n'
        "-->"
    )

    prepared = prepare_report_for_output(report)

    assert prepared.chart_data["health_score"] == 75
    assert extract_chart_data(report)["health_score"] == 75

    is_chart_export_available.cache_clear()
    if is_chart_export_available():
        assert render_chart_pngs(prepared.chart_data).images
