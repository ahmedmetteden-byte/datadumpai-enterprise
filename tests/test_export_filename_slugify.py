"""
Regression tests: report/export filenames must be ASCII-safe storage keys.

Supabase Storage rejects keys containing characters like em-dashes with a
400 InvalidKey error — report titles built from template/period names (e.g.
"Executive Summary — Custom / Ad hoc") used to pass straight through.
"""

from __future__ import annotations

from services.export_service import ExportService
from services.report_service import ReportService


def test_export_service_slugify_strips_em_dash_and_slash():
    slug = ExportService()._slugify("Executive Summary — Custom / Ad hoc")
    assert slug == "executive_summary_custom_ad_hoc"
    assert slug.isascii()
    assert "/" not in slug


def test_report_service_slugify_strips_em_dash_and_slash():
    slug = ReportService._slugify_report_name("Executive Summary — Custom / Ad hoc")
    assert slug == "executive_summary_custom_ad_hoc"
    assert slug.isascii()
    assert "/" not in slug


def test_slugify_falls_back_to_report_when_nothing_survives():
    assert ExportService()._slugify("—— // ??") == "report"
    assert ReportService._slugify_report_name("—— // ??") == "report"
