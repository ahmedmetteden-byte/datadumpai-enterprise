"""
Tests for the quantitative-analysis-to-chart bridge (Step D of the
Premium Report Generation Upgrade): charts built directly from
quantitative_analysis_service's calculated MetricSeries output, instead
of being re-parsed from rendered narrative text.
"""

from __future__ import annotations

from services.quantitative_chart_bridge import (
    metric_series_to_chart_data,
    select_chart_candidates,
)
from services.visualization_engine import VisualizationStrategy

PREMIUM_SERIES = {
    "title": "Gross Premium",
    "source_document": "report.pdf",
    "unit": "₦ billion",
    "rows": [
        {"label": "2022", "value": 789.6},
        {"label": "2023", "value": 1043.1},
        {"label": "2024", "value": 1558.7},
    ],
    "calculations": {
        "period_over_period": [
            {"from": "2022", "to": "2023", "absolute": 253.5, "percent": 32.1},
            {"from": "2023", "to": "2024", "absolute": 515.6, "percent": 49.4},
        ],
        "total_change": {"from": "2022", "to": "2024", "absolute": 769.1, "percent": 97.4},
    },
}

MARKET_SHARE_SERIES = {
    "title": "Segment Market Share",
    "source_document": "report.pdf",
    "unit": "%",
    "rows": [
        {"label": "Life", "value": 32.0},
        {"label": "Non-Life", "value": 68.0},
    ],
    "calculations": {},
}


def test_metric_series_to_chart_data_temporal_series_becomes_line_chart():
    chart_data = metric_series_to_chart_data(PREMIUM_SERIES)

    assert chart_data["type"] == "LINE_CHART"
    trends = chart_data["data"]["trends"]
    assert trends == [
        {"label": "2023", "prior": 789.6, "current": 1043.1},
        {"label": "2024", "prior": 1043.1, "current": 1558.7},
    ]


def test_metric_series_to_chart_data_categorical_series_becomes_bar_chart():
    chart_data = metric_series_to_chart_data(MARKET_SHARE_SERIES)

    assert chart_data["type"] == "BAR_CHART"
    assert chart_data["data"]["series"] == [
        {"label": "Life", "value": 32.0},
        {"label": "Non-Life", "value": 68.0},
    ]


def test_metric_series_to_chart_data_returns_none_for_fewer_than_two_rows():
    series = {**PREMIUM_SERIES, "rows": [{"label": "2024", "value": 1558.7}]}
    assert metric_series_to_chart_data(series) is None


def test_select_chart_candidates_only_builds_charts_for_requirements():
    requirements = [
        {"strategy": "LINE_CHART", "metric_title": "Gross Premium", "reason": "materiality"},
    ]
    blocks = select_chart_candidates([PREMIUM_SERIES, MARKET_SHARE_SERIES], requirements)

    assert len(blocks) == 1
    block = blocks[0]
    assert block.title == "Gross Premium"
    assert block.type == VisualizationStrategy.LINE_CHART
    assert block.unit == "₦ billion"
    assert block.x_label == "Period"
    assert block.y_label == "Gross Premium (₦ billion)"
    assert block.data["trends"][0]["current"] == 1043.1


def test_select_chart_candidates_skips_requirement_with_no_matching_table():
    requirements = [
        {"strategy": "LINE_CHART", "metric_title": "Nonexistent Metric", "reason": "x"},
    ]
    blocks = select_chart_candidates([PREMIUM_SERIES], requirements)
    assert blocks == []


def test_select_chart_candidates_preserves_requirement_order_as_priority():
    requirements = [
        {"strategy": "BAR_CHART", "metric_title": "Segment Market Share", "reason": "x"},
        {"strategy": "LINE_CHART", "metric_title": "Gross Premium", "reason": "y"},
    ]
    blocks = select_chart_candidates([PREMIUM_SERIES, MARKET_SHARE_SERIES], requirements)

    assert [b.title for b in blocks] == ["Segment Market Share", "Gross Premium"]
    assert [b.priority for b in blocks] == [1, 2]


def test_select_chart_candidates_kill_switch_disables_bridge(monkeypatch):
    monkeypatch.setattr(
        "services.quantitative_chart_bridge.REPORT_CHART_METRIC_BRIDGE_ENABLED", False
    )
    requirements = [
        {"strategy": "LINE_CHART", "metric_title": "Gross Premium", "reason": "x"},
    ]
    blocks = select_chart_candidates([PREMIUM_SERIES], requirements)
    assert blocks == []


def test_select_chart_candidates_no_generic_labels_ever():
    requirements = [
        {"strategy": "LINE_CHART", "metric_title": "Gross Premium", "reason": "x"},
        {"strategy": "BAR_CHART", "metric_title": "Segment Market Share", "reason": "y"},
    ]
    blocks = select_chart_candidates([PREMIUM_SERIES, MARKET_SHARE_SERIES], requirements)

    for block in blocks:
        assert block.x_label not in ("Metric", "x", "X")
        assert block.y_label not in ("Value", "y")
