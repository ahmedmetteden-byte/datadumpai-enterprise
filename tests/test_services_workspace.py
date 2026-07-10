"""
Unit tests for WorkspaceService.
"""

from __future__ import annotations

from models.knowledge import KnowledgeStore
from models.workspace import WorkspaceAI, WorkspaceAnalytics
from services.document_service import DocumentService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.workspace_service import WorkspaceService
from tests.conftest import MockUpload


def test_load_workspace_assembles_facets(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Workspace Assembly")

    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Workspace notes."),
    )

    ReportService.save_report(
        project["id"],
        "Status Report",
        "# Status Report\n\nAll systems operational.",
    )

    workspace = WorkspaceService().load_workspace(project["id"])

    assert workspace.id == project["id"]
    assert workspace.name == "Workspace Assembly"
    assert isinstance(workspace.ai, WorkspaceAI)
    assert isinstance(workspace.analytics, WorkspaceAnalytics)
    assert isinstance(workspace.knowledge, KnowledgeStore)
    assert workspace.document_count == 1
    assert workspace.report_count == 1
    assert workspace.document_count == len(workspace.documents)
    assert workspace.report_count == len(workspace.reports)


def test_workspace_ai_ready_when_documents_exist(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("AI Ready Workspace")

    document_service.save_document(
        project["id"],
        MockUpload("source.txt", b"Source material."),
    )

    workspace = WorkspaceService().load_workspace(project["id"])

    assert workspace.ai.ready is True
    assert workspace.ai.status == "AI ready"


def test_workspace_analytics_match_disk_counts(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Analytics Workspace")

    document_service.save_document(
        project["id"],
        MockUpload("a.txt", b"A"),
    )
    document_service.save_document(
        project["id"],
        MockUpload("b.txt", b"B"),
    )

    workspace = WorkspaceService().load_workspace(project["id"])

    assert workspace.analytics.document_count == 2
    assert workspace.storage_used > 0
    assert workspace.knowledge.source_count >= 2
