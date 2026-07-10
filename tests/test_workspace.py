"""
Tests for Workspace domain assembly, core facade, and Knowledge Store.
"""

from __future__ import annotations

from core.workspace import Workspace
from core.workspace_context import QUICK_REPORT_PROJECT_ID
from models.knowledge import KnowledgeStore
from models.workspace import (
    WorkspaceAI,
    WorkspaceAnalytics,
)
from services.document_service import DocumentService
from services.knowledge_service import KnowledgeService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.workspace_service import WorkspaceService
from tests.conftest import MockUpload


def test_load_workspace_returns_domain_object(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Workspace Test Project")
    service = WorkspaceService()

    data = service.load_workspace(project["id"])

    assert data.id == project["id"]
    assert data.name == "Workspace Test Project"


def test_load_quick_report_workspace(isolated_env):
    service = WorkspaceService()

    data = service.load_workspace(QUICK_REPORT_PROJECT_ID)

    assert data.id == QUICK_REPORT_PROJECT_ID
    assert data.name == "Quick Report"


def test_workspace_has_all_core_facets(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Facet Project")
    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Facet notes."),
    )
    service = WorkspaceService()

    data = service.load_workspace(project["id"])

    assert data.project
    assert isinstance(data.documents, list)
    assert isinstance(data.reports, list)
    assert isinstance(data.ai, WorkspaceAI)
    assert isinstance(data.timeline, list)
    assert isinstance(data.analytics, WorkspaceAnalytics)
    assert isinstance(data.exports, list)
    assert isinstance(data.knowledge, KnowledgeStore)


def test_workspace_analytics_match_collections(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Analytics Project")
    document_service.save_document(
        project["id"],
        MockUpload("a.txt", b"A"),
    )
    ReportService.save_report(
        project["id"],
        "Status Report",
        "# Status Report\n\nDone.",
    )
    service = WorkspaceService()

    data = service.load_workspace(project["id"])

    assert data.document_count == len(data.documents)
    assert data.report_count == len(data.reports)
    assert data.export_count == len(data.exports)


def test_workspace_ai_ready_when_documents_exist(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("AI Ready Project")
    document_service.save_document(
        project["id"],
        MockUpload("source.txt", b"Source material."),
    )
    service = WorkspaceService()

    data = service.load_workspace(project["id"])

    assert data.ai.ready is True
    assert data.ai.status == "AI ready"


def test_knowledge_store_indexes_sources(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Knowledge Project")
    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Knowledge notes."),
    )

    store = KnowledgeService().build_store(project["id"])

    assert isinstance(store, KnowledgeStore)
    assert store.source_count == len(store.entries)
    assert store.document_count + store.meeting_count <= store.source_count

    types = {entry.source_type for entry in store.entries}
    assert "document" in types or "report" in types or "timeline" in types


def test_workspace_includes_knowledge_store(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Knowledge Workspace")
    data = WorkspaceService().load_workspace(project["id"])

    assert isinstance(data.knowledge, KnowledgeStore)
    assert data.knowledge.source_count == len(data.knowledge.entries)


def test_core_workspace_facade(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
):
    project = project_service.create_project("Facade Project")
    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Notes."),
    )

    workspace = Workspace(project["id"])

    assert workspace.project_id == project["id"]
    assert workspace.name == "Facade Project"
    assert isinstance(workspace.documents, list)
    assert isinstance(workspace.reports, list)
    assert isinstance(workspace.storage, int)
    assert workspace.document_count == len(workspace.documents)
    assert workspace.report_count == len(workspace.reports)
    assert isinstance(workspace.project, dict)
    assert "id" in workspace.project
    assert isinstance(workspace.knowledge, KnowledgeStore)
