"""
Tests for ReportService and Reports Workspace disk listing.
"""

from __future__ import annotations

from pathlib import Path

from core.workspace import Workspace
from services.document_service import DocumentService
from services.project_service import ProjectService
from services.report_service import ReportService
from tests.conftest import MockUpload


def test_get_reports_reads_from_disk(isolated_env, project_service: ProjectService):
    project = project_service.create_project("Reports Test Project")
    ReportService.save_report(
        project["id"],
        "Executive Summary",
        "# Executive Summary\n\nDisk report.",
    )

    reports = ReportService.get_reports(project["id"])

    assert isinstance(reports, list)
    assert len(reports) == 1

    for report in reports:
        assert "filename" in report
        assert "name" in report
        assert "path" in report
        assert "size" in report
        assert Path(report["path"]).is_file()
        assert report["filename"].endswith(".md")


def test_load_report_returns_content_from_disk(isolated_env, project_service: ProjectService):
    project = project_service.create_project("Load Report Project")
    metadata = ReportService.save_report(
        project["id"],
        "Executive Summary",
        "# Executive Summary\n\nLoaded content.",
    )

    text = ReportService.load_report(metadata["path"])

    assert isinstance(text, str)
    assert "Loaded content" in text


def test_workspace_reports_match_disk(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Workspace Reports Project")
    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Workspace notes."),
    )
    ReportService.save_report(
        project["id"],
        "Status Report",
        "# Status Report\n\nAll good.",
    )

    workspace = Workspace(project["id"])
    disk_reports = ReportService.get_reports(project["id"])

    assert workspace.report_count == len(disk_reports)
    assert len(workspace.reports) == len(disk_reports)

    workspace_names = {report["filename"] for report in workspace.reports}
    disk_names = {report["filename"] for report in disk_reports}

    assert workspace_names == disk_names


def test_save_report_persists_to_disk(isolated_env):
    project_id = ProjectService().create_project("Reports Disk Project")["id"]

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
