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
        "unit": "%",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Segment"
    # The y-axis no longer carries a rotated title string at all (a long/
    # redundant title was found to overflow Kaleido's rotated-text layout
    # and render corrupted in real production PDFs — see
    # _axis_tick_format's docstring). The unit is instead conveyed via
    # tick formatting and on-bar value labels.
    assert not figure.layout.yaxis.title.text
    assert figure.layout.yaxis.ticksuffix == "%"
    assert list(figure.data[0].text) == ["32.0%", "68.0%"]


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
        "unit": "$ million",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text != "Metric"
    # No generic "Value" axis title, and no unformatted raw numbers either
    # — each bar states its own real, unit-formatted value.
    assert list(figure.data[0].text) == ["$1,043.1m", "$1,558.7m"]
    assert figure.layout.yaxis.tickprefix == "$"


def test_kpi_cards_gets_real_axis_labels_not_literal_x_y():
    block = {
        "type": "KPI_CARDS",
        "title": "Key Performance Indicators",
        "data": {"items": [{"label": "Gross Premium", "value": 1558.7, "unit": "$ million"}]},
        "x_label": "Metric",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Metric"
    assert figure.layout.xaxis.title.text != "x"
    assert not figure.layout.yaxis.title.text
    assert figure.layout.yaxis.title.text != "y"
    assert list(figure.data[0].text) == ["$1,558.7m"]


def test_line_chart_uses_block_provided_axis_labels():
    block = {
        "type": "LINE_CHART",
        "title": "Gross Premium",
        "data": {"trends": [{"label": "2024", "prior": 1043.1, "current": 1558.7}]},
        "x_label": "Period",
        "unit": "$ billion",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Period"
    assert figure.layout.yaxis.title.text is None
    assert figure.layout.yaxis.ticksuffix == "bn"
    # First and last points are labeled with real, unit-formatted values —
    # via trace-native text, never figure.add_annotation(). A category
    # x-axis annotation was found to collapse every point in the trace
    # onto a single x position under Kaleido's static-image renderer
    # (confirmed by direct reproduction), so on-chart point labels must
    # never use that mechanism.
    assert not figure.layout.annotations
    assert list(figure.data[0].text) == ["$1,043.10bn", "$1,558.70bn"]


def test_line_chart_abbreviates_full_month_name_period_labels():
    """Phase C.1 (Section 10): "January 2026" style tick labels are
    abbreviated to "Jan 2026" so a handful of period ticks don't crowd
    the chart — an explicit requirement ("dates/months displayed
    cleanly"), not just a styling nicety."""

    block = {
        "type": "LINE_CHART",
        "title": "Claims Incurred",
        "data": {
            "points": [
                {"label": "January 2026", "value": 82.1},
                {"label": "February 2026", "value": 91.8},
                {"label": "March 2026", "value": 89.7},
            ]
        },
        "x_label": "Period",
        "unit": "$ million",
    }
    _title, figure = _figure_from_visualization_block(block)
    assert list(figure.data[0].x) == ["Jan 2026", "Feb 2026", "Mar 2026"]


def test_bar_chart_abbreviates_full_month_name_labels_too():
    block = {
        "type": "BAR_CHART",
        "title": "Claims Backlog",
        "data": {
            "series": [
                {"label": "January 2026", "value": 418},
                {"label": "March 2026", "value": 431},
            ]
        },
        "x_label": "Period",
        "unit": "cases",
    }
    _title, figure = _figure_from_visualization_block(block)
    assert list(figure.data[0].x) == ["Jan 2026", "Mar 2026"]


def test_chart_axis_label_leaves_non_period_category_names_unchanged():
    """The abbreviation must never touch a label it doesn't recognize as
    a full-month-name period — a category name, a channel name, or a
    filename that leaked in must pass through byte-for-byte."""

    from services.report_chart_figures import _chart_axis_label

    assert _chart_axis_label("Digital") == "Digital"
    assert _chart_axis_label("Q1 2026") == "Q1 2026"
    assert _chart_axis_label("Western Region") == "Western Region"
    assert _chart_axis_label("2026") == "2026"


def test_line_chart_three_period_series_shows_every_period_on_the_x_axis():
    """Regression test for the confirmed chart x-axis bug: a 3-period
    series must show ALL THREE periods as their own x-axis positions,
    with each point plotted under its own correct label — not the old
    "Previous vs Current" pairwise design, which silently dropped the
    first period (2023) from the axis entirely and plotted its value
    under the SECOND period's label instead."""

    block = {
        "type": "LINE_CHART",
        "title": "Gross Premium",
        "data": {
            "points": [
                {"label": "2023", "value": 1200.0},
                {"label": "2024", "value": 1367.0},
                {"label": "2025", "value": 1567.0},
            ]
        },
        "x_label": "Period",
        "y_label": "Gross Premium ($m)",
    }
    _title, figure = _figure_from_visualization_block(block)

    assert len(figure.data) == 1
    trace = figure.data[0]
    assert list(trace.x) == ["2023", "2024", "2025"]
    assert list(trace.y) == [1200.0, 1367.0, 1567.0]


def test_line_chart_legacy_trends_shape_still_renders_via_fallback():
    """Already-persisted report chart data (saved before this fix) used
    the old {label, prior, current} pairwise shape. The renderer must
    still handle it gracefully — recovering the first point's value
    (previously silently mislabeled under the second period) with a
    blank label rather than a wrong one, and every subsequent point
    correctly labeled and valued."""

    block = {
        "type": "LINE_CHART",
        "title": "Gross Premium",
        "data": {
            "trends": [
                {"label": "2024", "prior": 1200.0, "current": 1367.0},
                {"label": "2025", "prior": 1367.0, "current": 1567.0},
            ]
        },
        "x_label": "Period",
        "y_label": "Gross Premium ($m)",
    }
    _title, figure = _figure_from_visualization_block(block)

    trace = figure.data[0]
    assert list(trace.x) == ["", "2024", "2025"]
    assert list(trace.y) == [1200.0, 1367.0, 1567.0]


def test_line_chart_omits_when_multiple_points_collapse_to_one_x_position():
    """Phase 3 Step 2 defensive guard (exercised here via the legacy
    fallback path): if every trend point were ever tagged with the same
    period label (e.g. a categorical series mis-classified as temporal
    upstream), rendering a connected line across a single collapsed
    x-axis position would read as a real trend where none exists — omit
    the chart rather than render that."""

    block = {
        "type": "LINE_CHART",
        "title": "Complaint Rate",
        "data": {
            "trends": [
                {"label": "2025", "prior": 3.2, "current": 2.1},
                {"label": "2025", "prior": 2.1, "current": 1.8},
                {"label": "2025", "prior": 1.8, "current": 7.4},
            ]
        },
        "x_label": "Period",
        "y_label": "Complaint Rate (%)",
    }
    assert _figure_from_visualization_block(block) is None


def test_line_chart_single_trend_point_is_still_rendered():
    """A single Previous-vs-Current transition legitimately has exactly
    one label — must not be caught by the collapsed-axis guard above."""

    block = {
        "type": "LINE_CHART",
        "title": "Claims Backlog",
        "data": {"trends": [{"label": "Q4 2025", "prior": 14, "current": 31}]},
        "x_label": "Period",
        "y_label": "Claims Backlog",
    }
    result = _figure_from_visualization_block(block)
    assert result is not None


# --- Phase D cleanup: first/last data-point label positioning ---
#
# Confirmed against a real export: a fixed "top right" for the first
# point put its label directly in the path of an ASCENDING first
# segment's own line stroke (the label and the rising line occupy the
# same up-right direction from the point), rendering the value crossed
# out. The fix chooses top vs. bottom for the first/last point based on
# the LOCAL segment's slope, so the label lands on whichever side the
# adjacent line segment is NOT occupying. These tests check the
# renderer's positioning decision (figure.data[0].textposition), not
# rendered pixel output, per the guidance to avoid brittle
# pixel-coordinate tests.


def _line_chart_positions(points: list[dict], unit: str = "$ million") -> list[str]:
    block = {
        "type": "LINE_CHART",
        "title": "Metric",
        "data": {"points": points},
        "x_label": "Period",
        "unit": unit,
    }
    _title, figure = _figure_from_visualization_block(block)
    return list(figure.data[0].textposition)


def test_line_chart_label_position_avoids_an_ascending_first_segment():
    """The exact reproduced case: values rise sharply from the first
    point (82.1 -> 91.8 -> 89.7) — the first point's label must be
    placed on the "bottom" side, away from the rising line, not "top"
    where it would sit on the stroke."""

    positions = _line_chart_positions(
        [
            {"label": "January 2026", "value": 82.1},
            {"label": "February 2026", "value": 91.8},
            {"label": "March 2026", "value": 89.7},
        ]
    )
    assert positions[0] == "bottom right"
    # The final segment descends into the last point (91.8 -> 89.7) —
    # the incoming line arrives from above, so the label goes below.
    assert positions[-1] == "bottom left"


def test_line_chart_label_position_avoids_a_descending_first_segment():
    """The mirror case: values fall from the first point. Here "top" IS
    the clear side (the line descends away to the right), so the
    original top-right placement remains correct — the fix must not
    flip labels unconditionally, only when the adjacent segment's slope
    actually collides with the default side."""

    positions = _line_chart_positions(
        [
            {"label": "January 2026", "value": 91.8},
            {"label": "February 2026", "value": 82.1},
            {"label": "March 2026", "value": 89.7},
        ]
    )
    assert positions[0] == "top right"
    # The final segment ascends into the last point (82.1 -> 89.7) —
    # arrives from below, so "top left" (the default) remains clear.
    assert positions[-1] == "top left"


def test_line_chart_label_position_for_a_two_point_series():
    """A 2-point series has no "middle" point — first and last are the
    same two points the slope-aware rule must still handle correctly."""

    rising = _line_chart_positions(
        [{"label": "January 2026", "value": 100.0}, {"label": "February 2026", "value": 150.0}]
    )
    assert rising[0] == "bottom right"
    assert rising[-1] == "top left"

    falling = _line_chart_positions(
        [{"label": "January 2026", "value": 150.0}, {"label": "February 2026", "value": 100.0}]
    )
    assert falling[0] == "top right"
    assert falling[-1] == "bottom left"


def test_line_chart_label_position_for_small_and_large_value_ranges():
    """The slope comparison must work the same way regardless of the
    data's absolute scale — a small range (percentages) and a large
    range (millions) with the same shape must produce the same
    first-point placement."""

    small_range = _line_chart_positions(
        [
            {"label": "January 2026", "value": 64.0},
            {"label": "February 2026", "value": 68.2},
            {"label": "March 2026", "value": 64.3},
        ],
        unit="%",
    )
    large_range = _line_chart_positions(
        [
            {"label": "January 2026", "value": 128.4},
            {"label": "February 2026", "value": 134.7},
            {"label": "March 2026", "value": 139.6},
        ],
        unit="$ million",
    )
    assert small_range[0] == "bottom right"
    assert large_range[0] == "bottom right"


def test_line_chart_first_point_label_stays_legible_at_the_chart_boundary():
    """The first point sits at (or very near) the y-axis floor, the
    exact geometry the reported bug involved — even here the label must
    still be assigned a real, on-chart position rather than being
    dropped or left empty."""

    positions = _line_chart_positions(
        [
            {"label": "January 2026", "value": 82.1},
            {"label": "February 2026", "value": 82.15},
        ]
    )
    assert positions[0] in {"top right", "bottom right"}
    assert positions[0] != ""


def test_risk_matrix_has_meaningful_axis_labels():
    block = {
        "type": "RISK_MATRIX",
        "title": "Risk Matrix",
        "data": {"rows": [{"risk": "Oil & Gas concentration", "severity": 4}]},
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Risk"
    assert figure.layout.yaxis.title.text == "Severity"


def test_risk_matrix_renders_both_dimensions_when_likelihood_is_present():
    """Phase D: confirmed against a real export — a risk matrix with real
    likelihood data was rendering as a plain 1-D severity bar, silently
    dropping likelihood entirely. When likelihood IS present, it must
    render as a 2-D chart with likelihood on one axis, not disappear."""

    block = {
        "type": "RISK_MATRIX",
        "title": "Risk Matrix",
        "data": {
            "rows": [
                {"risk": "Regulatory change", "severity": 4, "likelihood": 1},
                {"risk": "Claims backlog", "severity": 8, "likelihood": 5},
            ]
        },
    }
    _title, figure = _figure_from_visualization_block(block)

    assert figure.layout.xaxis.title.text == "Likelihood"
    assert figure.layout.yaxis.title.text == "Severity"
    trace = figure.data[0]
    assert list(trace.x) == [1.0, 5.0]
    assert list(trace.y) == [4.0, 8.0]
    assert list(trace.text) == ["Regulatory change", "Claims backlog"]


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
