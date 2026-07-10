"""
Unit tests for ReportService.
"""

from __future__ import annotations

from pathlib import Path

from services.report_service import ReportService


def test_save_report_persists_to_disk(isolated_env):
    project_id = "report-service-project"

    metadata = ReportService.save_report(
        project_id,
        "Board Brief",
        "# Board Brief\n\nPersisted content.",
    )

    saved = Path(metadata["path"])

    assert saved.is_file()
    assert saved.read_text(encoding="utf-8").startswith("# Board Brief")

    listed = ReportService.get_reports(project_id)

    assert len(listed) == 1
    assert listed[0]["filename"] == "board_brief.md"
    assert listed[0]["name"] == "Board Brief"


def test_load_report_returns_content(isolated_env):
    project_id = "load-report-project"

    metadata = ReportService.save_report(
        project_id,
        "Executive Summary",
        "# Executive Summary\n\nKey findings.",
    )

    text = ReportService.load_report(metadata["path"])

    assert "Key findings" in text


def test_get_reports_empty_when_folder_missing(isolated_env):
    reports = ReportService.get_reports("missing-project-id")

    assert reports == []


def test_delete_report_removes_file(isolated_env):
    project_id = "delete-report-project"

    metadata = ReportService.save_report(
        project_id,
        "Board Report",
        "# Board Report\n\nContent.",
    )

    ReportService.delete_report(project_id, metadata["filename"])

    assert ReportService.get_reports(project_id) == []


def test_save_report_persists_metadata(isolated_env):
    project_id = "metadata-report-project"

    metadata = ReportService.save_report(
        project_id,
        "Executive Summary",
        "# Executive Summary\n\nContent.",
        source_documents=["notes.pdf", "budget.xlsx"],
    )

    loaded = ReportService.get_report_metadata(project_id, metadata["filename"])

    assert loaded["report_type"] == "Executive Summary"
    assert loaded["source_documents"] == ["notes.pdf", "budget.xlsx"]

    listed = ReportService.get_reports(project_id)

    assert listed[0]["source_documents"] == ["notes.pdf", "budget.xlsx"]


def test_update_report_overwrites_content_and_metadata(isolated_env):
    project_id = "update-report-project"

    metadata = ReportService.save_report(
        project_id,
        "Board Report",
        "# Board Report\n\nOriginal.",
        source_documents=["a.pdf"],
    )

    updated = ReportService.update_report(
        project_id,
        metadata["filename"],
        "# Board Report\n\nUpdated.",
        source_documents=["a.pdf", "b.docx"],
    )

    assert "Updated." in ReportService.load_report(updated["path"])
    assert updated["source_documents"] == ["a.pdf", "b.docx"]
