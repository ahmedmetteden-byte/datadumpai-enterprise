"""
Integration tests for ReportPipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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

    report, metadata = pipeline.generate_and_save(
        project=project,
        document_text="Source document text.",
        report_type="Executive Summary",
        source_documents=["notes.txt"],
        writing_style="Executive",
        audience="Board of Directors",
        include_charts=True,
        include_recommendations=True,
    )

    assert "Pipeline integration report" in report.narrative
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

    report, metadata = pipeline.generate_and_save(
        project=project,
        document_text="Original source.",
        report_type="Executive Summary",
        source_documents=["source.txt"],
    )

    assert "Original report" in report.narrative

    regenerated, updated = pipeline.regenerate_and_save(
        project=project,
        report=metadata,
    )

    assert "Regenerated report" in regenerated.narrative
    assert updated["filename"] == metadata["filename"]
    assert ReportService.load_report(updated["path"]) == regenerated.to_markdown()
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

    combined = ReportPipeline(
        current_user=document_service.current_user,
        document_service=document_service,
        project_service=project_service,
    ).load_document_text_from_selection(selection)

    assert "=== SOURCE DOCUMENT: alpha.txt ===" in combined["combined_text"]
    assert "=== SOURCE DOCUMENT: beta.txt ===" in combined["combined_text"]
    assert "Alpha content." in combined["combined_text"]
    assert "Beta content." in combined["combined_text"]
    assert combined["loaded"] == ["alpha.txt", "beta.txt"]
    assert combined["skipped"] == []
    assert combined["multi_stage"] is False


def test_parallel_document_load_does_not_require_thread_local_auth(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
    monkeypatch,
):
    """Worker threads must reuse the pipeline user — not require_current_user()."""

    from core.current_user import (
        AuthenticationRequiredError,
        clear_current_user_binding,
        require_current_user,
    )
    from tests.conftest import MockUpload, TEST_USER

    project = project_service.create_project("Parallel Auth")
    document_service.save_document(
        project["id"],
        MockUpload("one.txt", b"First document."),
    )
    document_service.save_document(
        project["id"],
        MockUpload("two.txt", b"Second document."),
    )

    pipeline = ReportPipeline(
        current_user=document_service.current_user,
        access_token="captured-jwt",
        document_service=DocumentService(
            current_user=document_service.current_user,
            access_token="captured-jwt",
            file_store=document_service._file_store,
        ),
        project_service=project_service,
    )

    # Simulate production worker threads: no ContextVar override and no
    # Streamlit session user available via get_current_user().
    clear_current_user_binding()
    monkeypatch.setattr("core.auth.get_current_user", lambda: None)
    monkeypatch.setattr("core.auth.get_access_token", lambda: None)

    with pytest.raises(AuthenticationRequiredError):
        require_current_user()

    selection = [
        {"project_id": project["id"], "filename": "one.txt"},
        {"project_id": project["id"], "filename": "two.txt"},
    ]
    result = pipeline.load_document_text_from_selection(selection)

    assert result["loaded"] == ["one.txt", "two.txt"]
    assert "First document." in result["combined_text"]
    assert "Second document." in result["combined_text"]
    assert pipeline.current_user.id == TEST_USER.id
    assert pipeline.access_token == "captured-jwt"


def test_read_document_text_does_not_list_files(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
    monkeypatch,
):
    """Report reads must resolve the known storage key — never list_files()."""

    from tests.conftest import MockUpload

    project = project_service.create_project("Direct Read")
    document_service.save_document(
        project["id"],
        MockUpload("notes.txt", b"Direct path content."),
    )

    def boom(*_args, **_kwargs):
        raise AssertionError("list_files must not be used during read_document_text")

    monkeypatch.setattr(document_service._file_store, "list_files", boom)

    text = document_service.read_document_text(project["id"], "notes.txt")
    assert "Direct path content." in text


def test_file_store_supabase_client_uses_captured_access_token(monkeypatch):
    """Worker FileStore calls must pass the captured JWT — never session lookup."""

    from unittest.mock import MagicMock

    from core.database import DatabaseError
    from storage.file_store import FileStore
    from tests.conftest import TEST_USER

    def session_token_unavailable():
        raise AssertionError("get_access_token must not be called from FileStore workers")

    monkeypatch.setattr("core.auth.get_access_token", session_token_unavailable)

    seen: dict[str, str | None] = {}

    def fake_get_database_client(*, access_token: str | None = None):
        seen["access_token"] = access_token
        if not access_token:
            raise DatabaseError(
                "No authenticated session is available for database access."
            )
        return MagicMock()

    monkeypatch.setattr("core.database.get_database_client", fake_get_database_client)

    store = FileStore(TEST_USER, access_token="worker-jwt")
    store._supabase_client()

    assert seen["access_token"] == "worker-jwt"


def test_parallel_document_load_does_not_require_session_access_token(
    isolated_env,
    project_service: ProjectService,
    document_service: DocumentService,
    monkeypatch,
):
    """After construction, workers must never fall back to get_access_token()."""

    from core.current_user import clear_current_user_binding
    from core.database import DatabaseError
    from tests.conftest import MockUpload, TEST_USER

    project = project_service.create_project("Token Isolation")
    document_service.save_document(
        project["id"],
        MockUpload("one.txt", b"Token-safe document."),
    )

    bound = DocumentService(
        current_user=TEST_USER,
        access_token="captured-jwt",
        file_store=document_service._file_store,
    )
    # Ensure the bound store also carries the token for any supabase path.
    bound._file_store._access_token = "captured-jwt"

    pipeline = ReportPipeline(
        current_user=TEST_USER,
        access_token="captured-jwt",
        document_service=bound,
        project_service=ProjectService(
            current_user=TEST_USER,
            access_token="captured-jwt",
            document_service=bound,
        ),
    )

    clear_current_user_binding()
    monkeypatch.setattr("core.auth.get_current_user", lambda: None)

    def deny_session_token():
        raise AssertionError("session get_access_token must not run after construct")

    monkeypatch.setattr("core.auth.get_access_token", deny_session_token)

    def deny_unauthed_client(*, access_token: str | None = None):
        if not access_token:
            raise DatabaseError(
                "No authenticated session is available for database access."
            )
        from unittest.mock import MagicMock

        return MagicMock(name="authed-client")

    monkeypatch.setattr("core.database.get_database_client", deny_unauthed_client)

    result = pipeline.load_document_text_from_selection(
        [{"project_id": project["id"], "filename": "one.txt"}]
    )

    assert result["loaded"] == ["one.txt"]
    assert "Token-safe document." in result["combined_text"]


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

    report = pipeline.generate(
        document_text="Source document text.",
        report_type="Executive Summary",
    )

    assert "Draft only" in report.narrative
    assert ReportService.get_reports(project["id"]) == []
    ai.generate_report.assert_called_once()
