"""
Tests for the premium-vs-plain export routing decision (Step G of the
Premium Report Generation Upgrade). No such test existed before Step G —
report_is_intelligence() previously only had indirect coverage via
build_premium_pdf()'s own tests, never a direct test of the routing
decision itself, independent of actual export bytes.
"""

from __future__ import annotations

from models.report_data import ReportData
from services.report_document import report_is_intelligence


def test_legacy_heading_format_is_always_premium_eligible(monkeypatch):
    """The legacy Executive Intelligence Dashboard heading routes to
    premium regardless of the new kill-switch — this path predates Step
    G and must never regress."""

    monkeypatch.setattr("services.report_document.PREMIUM_EXPORT_ROUTING_ENABLED", False)
    report = ReportData(narrative="## Executive Intelligence Dashboard\nContent.")
    assert report_is_intelligence(report) is True


def test_spa_report_is_not_premium_eligible_when_kill_switch_disabled(monkeypatch):
    monkeypatch.setattr("services.report_document.PREMIUM_EXPORT_ROUTING_ENABLED", False)
    report = ReportData(
        narrative="## Executive Summary\nContent.",
        metrics={"tables": [{"title": "Gross Premium"}]},
    )
    assert report_is_intelligence(report) is False


def test_spa_report_with_metric_tables_is_premium_eligible_when_enabled(monkeypatch):
    monkeypatch.setattr("services.report_document.PREMIUM_EXPORT_ROUTING_ENABLED", True)
    report = ReportData(
        narrative="## Executive Summary\nContent.",
        metrics={"tables": [{"title": "Gross Premium"}]},
    )
    assert report_is_intelligence(report) is True


def test_spa_report_with_visualizations_is_premium_eligible_when_enabled(monkeypatch):
    monkeypatch.setattr("services.report_document.PREMIUM_EXPORT_ROUTING_ENABLED", True)
    report = ReportData(
        narrative="## Executive Summary\nContent.",
        charts={"visualizations": [{"title": "Gross Premium"}]},
    )
    assert report_is_intelligence(report) is True


def test_thin_spa_report_with_neither_metrics_nor_charts_falls_back_to_plain(monkeypatch):
    """A report with no real structured data shouldn't route to the
    premium renderer even when the flag is enabled — nothing there for
    it to build a genuine dashboard from."""

    monkeypatch.setattr("services.report_document.PREMIUM_EXPORT_ROUTING_ENABLED", True)
    report = ReportData(narrative="## Executive Summary\nJust prose, no data.")
    assert report_is_intelligence(report) is False


def test_kill_switch_defaults_to_false():
    """Flipping this on changes what real users see in every export for
    an eligible report — it must never accidentally default on."""

    from services import report_document

    assert report_document.PREMIUM_EXPORT_ROUTING_ENABLED is False
