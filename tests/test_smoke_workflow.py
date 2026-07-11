"""
Smoke test for the core DataDumpAI workflow.

create project → upload document → generate report → save report → open report
"""

from __future__ import annotations

from unittest.mock import MagicMock

from application.document_pipeline import DocumentPipeline
from application.report_pipeline import ReportPipeline
from services.document_service import DocumentService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.workspace_service import WorkspaceService
from tests.conftest import MockUpload


def test_core_workflow_smoke(isolated_env):
    """
    Verify the main end-to-end workflow without calling external AI APIs.
    """

    project_service = ProjectService(
        document_service=DocumentService(
            projects_root=isolated_env["root"]
        )
    )
    document_service = DocumentService(
        projects_root=isolated_env["root"]
    )

    # 1. Create project
    project = project_service.create_project("Smoke Test Project")

    # 2. Upload document
    document_pipeline = DocumentPipeline(
        document_service=document_service,
        project_service=project_service,
    )
    project = document_pipeline.get_project_with_documents(project["id"])

    document_text, _processed, _new_count = document_pipeline.ingest(
        project=project,
        uploaded_files=[
            MockUpload(
                "smoke_input.txt",
                b"Revenue grew 12 percent. Key risk: supply chain.",
            )
        ],
    )

    assert document_text

    # 3. Generate report (AI mocked)
    ai = MagicMock()
    ai.generate_report.return_value = (
        "# Executive Summary\n\n"
        "Revenue grew 12 percent.\n\n"
        "## Risks\n\n"
        "- Supply chain exposure remains unresolved."
    )

    report_pipeline = ReportPipeline(
        ai_service=ai,
        project_service=project_service,
    )

    project = project_service.get_project(project["id"])
    project["documents"] = document_service.get_documents(project["id"])

    report, metadata = report_pipeline.generate_and_save(
        project=project,
        document_text=document_text,
        report_type="Executive Summary",
        source_documents=["smoke_input.txt"],
        writing_style="Executive",
        audience="Board of Directors",
        include_charts=False,
        include_recommendations=True,
    )

    # 4. Save report (via pipeline) and verify on disk
    assert metadata["path"]
    reports = ReportService.get_reports(project["id"])
    assert len(reports) == 1

    # 5. Open report
    opened = ReportService.load_report(reports[0]["path"])

    assert opened == report.to_markdown()
    assert "Supply chain" in opened

    # Workspace reflects the completed workflow
    workspace = WorkspaceService().load_workspace(project["id"])

    assert workspace.document_count == 1
    assert workspace.report_count == 1
    assert workspace.ai.ready is True
