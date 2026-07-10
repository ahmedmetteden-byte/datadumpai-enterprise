"""
Tests for Executive Copilot context assembly.
"""

from __future__ import annotations

from services.copilot_context_service import CopilotContextService
from services.document_service import DocumentService
from services.project_service import ProjectService
from services.report_service import ReportService
from tests.conftest import MockUpload


def test_copilot_context_includes_project_overview(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Copilot Project")
    service = CopilotContextService()

    workspace, context, _sources = service.build(
        project_id=project["id"],
        question="Summarize the last three reports.",
    )

    assert workspace.name == "Copilot Project"
    assert "ACTIVE PROJECT" in context
    assert workspace.name in context


def test_copilot_context_includes_reports_index(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Copilot Reports Project")
    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Copilot notes."),
    )
    ReportService.save_report(
        project["id"],
        "Executive Summary",
        "# Executive Summary\n\nSummary content.",
    )
    service = CopilotContextService()

    _workspace, context, sources = service.build(
        project_id=project["id"],
        question="What recommendations have been made?",
    )

    assert _workspace.report_count == 1
    assert "REPORTS INDEX" in context
    assert "RECENT REPORTS" in context
    assert sources


def test_copilot_context_with_focus_report(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Focused Copilot Project")
    ReportService.save_report(
        project["id"],
        "Executive Summary",
        "# Executive Summary\n\nFocused content.",
    )
    service = CopilotContextService()

    reports = service._workspace.load_workspace(project["id"]).reports

    _workspace, context, sources = service.build(
        project_id=project["id"],
        question="Summarize this report.",
        focus_report=reports[0],
    )

    assert "FOCUSED REPORT" in context
    assert reports[0]["name"] in sources
