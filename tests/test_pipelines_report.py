"""
Integration tests for ReportPipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from application.report_pipeline import ReportPipeline
from services.document_service import DocumentService
from services.project_service import ProjectService
from services.report_service import ReportService


def test_report_pipeline_generate_and_save(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Report Pipeline")

    ai = MagicMock()
    ai.generate_report.return_value = (
        "# Executive Summary\n\nPipeline integration report."
    )

    pipeline = ReportPipeline(
        ai_service=ai,
        project_service=project_service,
    )

    report_text, metadata = pipeline.generate_and_save(
        project=project,
        document_text="Source document text.",
        report_type="Executive Summary",
        source_documents=["notes.txt"],
        writing_style="Executive",
        audience="Board of Directors",
        include_charts=True,
        include_recommendations=True,
    )

    assert "Pipeline integration report" in report_text
    assert metadata["filename"] == "executive_summary.md"

    reports = ReportService.get_reports(project["id"])

    assert len(reports) == 1
    assert "Pipeline integration report" in ReportService.load_report(
        reports[0]["path"]
    )

    updated = project_service.get_project(project["id"])

    assert len(updated["reports"]) == 1
    ai.generate_report.assert_called_once()


def test_report_pipeline_regenerate_and_save(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    from tests.conftest import MockUpload

    project = project_service.create_project("Regenerate Pipeline")

    document_service.save_document(
        project["id"],
        MockUpload("source.txt", b"Updated source material."),
    )

    ai = MagicMock()
    ai.generate_report.side_effect = [
        "# Executive Summary\n\nOriginal report.",
        "# Executive Summary\n\nRegenerated report.",
    ]

    pipeline = ReportPipeline(
        ai_service=ai,
        project_service=project_service,
        document_service=document_service,
    )

    report_text, metadata = pipeline.generate_and_save(
        project=project,
        document_text="Original source.",
        report_type="Executive Summary",
        source_documents=["source.txt"],
    )

    assert "Original report" in report_text

    regenerated_text, updated = pipeline.regenerate_and_save(
        project=project,
        report=metadata,
    )

    assert "Regenerated report" in regenerated_text
    assert updated["filename"] == metadata["filename"]
    assert ReportService.load_report(updated["path"]) == regenerated_text
    assert ai.generate_report.call_count == 2


def test_load_document_text_from_selection_combines_all_documents(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    from tests.conftest import MockUpload

    project = project_service.create_project("Multi Doc")

    document_service.save_document(
        project["id"],
        MockUpload("alpha.txt", b"Alpha content."),
    )
    document_service.save_document(
        project["id"],
        MockUpload("beta.txt", b"Beta content."),
    )

    selection = [
        {"project_id": project["id"], "filename": "alpha.txt"},
        {"project_id": project["id"], "filename": "beta.txt"},
    ]

    combined = ReportPipeline.load_document_text_from_selection(selection)

    assert "=== SOURCE DOCUMENT: alpha.txt ===" in combined["combined_text"]
    assert "=== SOURCE DOCUMENT: beta.txt ===" in combined["combined_text"]
    assert "Alpha content." in combined["combined_text"]
    assert "Beta content." in combined["combined_text"]
    assert combined["loaded"] == ["alpha.txt", "beta.txt"]
    assert combined["skipped"] == []
    assert combined["truncated"] is False


def test_report_pipeline_generate_without_save(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Generate Only")

    ai = MagicMock()
    ai.generate_report.return_value = "# Executive Summary\n\nDraft only."

    pipeline = ReportPipeline(
        ai_service=ai,
        project_service=project_service,
    )

    report_text = pipeline.generate(
        document_text="Source document text.",
        report_type="Executive Summary",
    )

    assert "Draft only" in report_text
    assert ReportService.get_reports(project["id"]) == []
    ai.generate_report.assert_called_once()
