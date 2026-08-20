"""Tests for the shared Plotly chart figure pipeline."""

from __future__ import annotations

import pytest

from services.report_chart_data import extract_chart_data, prepare_report_for_output
from services.report_chart_export import is_chart_export_available, render_chart_pngs
from services.report_chart_figures import (
    _figure_from_visualization_block,
    build_report_chart_figures,
)

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


# Step D regression coverage: no chart may fall back to the old hardcoded
# "Metric"/"Value"/literal "x"/"y" axis labels — this is the exact bug
# that reached real downloaded PDF/DOCX files (see the report quality
# upgrade audit). No such assertions existed anywhere before Step D.


def test_bar_chart_uses_block_provided_axis_labels():
    block = {
        "type": "BAR_CHART",
        "title": "Segment Market Share",
        "data": {
            "series": [
                {"label": "Life", "value": 32.0},
                {"label": "Non-Life", "value": 68.0},
            ]
        },
        "x_label": "Segment",
        "y_label": "Market Share (%)",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Segment"
    assert figure.layout.yaxis.title.text == "Market Share (%)"


def test_bar_chart_never_falls_back_to_generic_metric_value_labels():
    block = {
        "type": "BAR_CHART",
        "title": "Gross Premium",
        "data": {
            "series": [
                {"label": "2023", "value": 1043.1},
                {"label": "2024", "value": 1558.7},
            ]
        },
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text != "Metric"
    assert figure.layout.yaxis.title.text != "Value"
    assert figure.layout.yaxis.title.text == "Gross Premium"  # falls back to the block's own title


def test_kpi_cards_gets_real_axis_labels_not_literal_x_y():
    block = {
        "type": "KPI_CARDS",
        "title": "Key Performance Indicators",
        "data": {"items": [{"label": "Gross Premium", "value": 1558.7}]},
        "x_label": "Metric",
        "y_label": "₦ billion",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Metric"
    assert figure.layout.yaxis.title.text == "₦ billion"
    assert figure.layout.xaxis.title.text != "x"
    assert figure.layout.yaxis.title.text != "y"


def test_line_chart_uses_block_provided_axis_labels():
    block = {
        "type": "LINE_CHART",
        "title": "Gross Premium",
        "data": {"trends": [{"label": "2024", "prior": 1043.1, "current": 1558.7}]},
        "x_label": "Period",
        "y_label": "Gross Premium (₦ billion)",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Period"
    assert figure.layout.yaxis.title.text == "Gross Premium (₦ billion)"


def test_risk_matrix_has_meaningful_axis_labels():
    block = {
        "type": "RISK_MATRIX",
        "title": "Risk Matrix",
        "data": {"rows": [{"risk": "Oil & Gas concentration", "severity": 4}]},
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Risk"
    assert figure.layout.yaxis.title.text == "Severity"


def test_decision_matrix_and_organizational_flow_have_meaningful_x_labels():
    decision_block = {
        "type": "DECISION_MATRIX",
        "title": "Decision Matrix",
        "data": {"rows": [{"party": "Plaintiff"}]},
    }
    _title, figure = _figure_from_visualization_block(decision_block)
    assert figure.layout.xaxis.title.text == "Party"

    flow_block = {
        "type": "ORGANIZATIONAL_FLOW",
        "title": "Stakeholder Map",
        "data": {"nodes": [{"label": "Objectives"}]},
    }
    _title, figure = _figure_from_visualization_block(flow_block)
    assert figure.layout.xaxis.title.text == "Stakeholder"
