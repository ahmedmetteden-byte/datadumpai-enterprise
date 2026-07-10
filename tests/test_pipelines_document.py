"""
Integration tests for DocumentPipeline.
"""

from __future__ import annotations

from application.document_pipeline import DocumentPipeline
from services.document_service import DocumentService
from services.project_service import ProjectService


def test_document_pipeline_ingest_persists_files(
    isolated_env,
    project_service: ProjectService,
    text_upload,
):
    document_service = DocumentService(
        projects_root=isolated_env["root"]
    )
    pipeline = DocumentPipeline(
        document_service=document_service,
        project_service=project_service,
    )

    project = pipeline.get_project_with_documents(
        project_service.create_project("Pipeline Ingest")["id"]
    )

    document_text, processed, new_count = pipeline.ingest(
        project=project,
        uploaded_files=[text_upload],
    )

    assert new_count == 1

    assert "Board meeting minutes" in document_text
    assert len(processed) == 1

    reloaded = pipeline.get_project_with_documents(project["id"])

    assert len(reloaded["documents"]) == 1
    assert reloaded["documents"][0]["filename"] == "board_minutes.txt"
    assert reloaded["storage_used"] > 0


def test_document_pipeline_reuses_existing_file(
    isolated_env,
    project_service: ProjectService,
    text_upload,
):
    document_service = DocumentService(
        projects_root=isolated_env["root"]
    )
    pipeline = DocumentPipeline(
        document_service=document_service,
        project_service=project_service,
    )

    project = pipeline.get_project_with_documents(
        project_service.create_project("Pipeline Reuse")["id"]
    )

    pipeline.ingest(project=project, uploaded_files=[text_upload])
    project = pipeline.get_project_with_documents(project["id"])

    _, processed_again, new_count = pipeline.ingest(
        project=project,
        uploaded_files=[text_upload],
    )

    assert new_count == 0

    assert len(processed_again) == 1
    assert len(project["documents"]) == 1


def test_document_pipeline_overwrite_replaces_file(
    isolated_env,
    project_service: ProjectService,
):
    from tests.conftest import MockUpload

    document_service = DocumentService(
        projects_root=isolated_env["root"]
    )
    pipeline = DocumentPipeline(
        document_service=document_service,
        project_service=project_service,
    )

    project = pipeline.get_project_with_documents(
        project_service.create_project("Pipeline Overwrite")["id"]
    )

    first_upload = MockUpload(
        "notes.txt",
        b"Original content.",
    )
    pipeline.ingest(project=project, uploaded_files=[first_upload])
    project = pipeline.get_project_with_documents(project["id"])

    second_upload = MockUpload(
        "notes.txt",
        b"Updated content with more detail.",
    )
    document_text, processed, new_count = pipeline.ingest(
        project=project,
        uploaded_files=[second_upload],
        overwrite=True,
    )

    assert new_count == 0

    assert "Updated content" in document_text
    assert len(processed) == 1
    assert len(project["documents"]) == 1
    assert project["documents"][0]["size"] > 0


def test_document_pipeline_can_skip_text_extraction_on_upload(
    isolated_env,
    project_service: ProjectService,
    text_upload,
):
    document_service = DocumentService(
        projects_root=isolated_env["root"]
    )
    pipeline = DocumentPipeline(
        document_service=document_service,
        project_service=project_service,
    )

    project = pipeline.get_project_with_documents(
        project_service.create_project("Pipeline Fast Upload")["id"]
    )

    document_text, processed, new_count = pipeline.ingest(
        project=project,
        uploaded_files=[text_upload],
        extract_text_on_upload=False,
    )

    assert new_count == 1
    assert document_text == ""
    assert len(processed) == 1
