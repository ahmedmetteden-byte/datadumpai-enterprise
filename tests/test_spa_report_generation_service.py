"""
Tests for free-text instructions threading through SpaReportGenerationService.
"""

from __future__ import annotations

from services.project_service import ProjectService
from services.report_service import ReportService
from services.spa_report_generation_service import (
    SpaReportGenerationService,
    _strip_wrapping_code_fence,
)


def test_strip_wrapping_code_fence_removes_markdown_fence():
    wrapped = '```markdown\n# Title\n\nSome text.\n```'
    assert _strip_wrapping_code_fence(wrapped) == '# Title\n\nSome text.'


def test_strip_wrapping_code_fence_removes_bare_fence():
    wrapped = '```\n# Title\n\nSome text.\n```'
    assert _strip_wrapping_code_fence(wrapped) == '# Title\n\nSome text.'


def test_strip_wrapping_code_fence_leaves_unfenced_text_alone():
    text = '# Title\n\nSome text with a `code span` in it.'
    assert _strip_wrapping_code_fence(text) == text


def test_strip_wrapping_code_fence_leaves_inline_fences_alone():
    # A fence that isn't wrapping the *entire* response shouldn't be touched.
    text = 'Some text.\n\n```python\nprint("hi")\n```\n\nMore text.'
    assert _strip_wrapping_code_fence(text) == text


def test_generate_includes_instructions_in_fallback_markdown(
    isolated_env, project_service: ProjectService, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Instructions Test Project")

    record = SpaReportGenerationService().generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
        instructions="Focus only on regulatory compliance risks.",
    )

    assert "Focus only on regulatory compliance risks." in record["content"]
    assert "User Instructions" in record["content"]


def test_generate_fallback_markdown_omits_leading_title_heading(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """The export layer renders the document title separately now — the
    generated body must start directly at '## Executive Summary', not a
    top-level '# {title}' heading that would show up twice in exports."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("No Duplicate Title Test Project")

    record = SpaReportGenerationService().generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
    )

    assert not record["content"].lstrip().startswith("# ")
    assert record["content"].lstrip().startswith("**Template:**")


def test_generate_without_instructions_omits_instructions_section(
    isolated_env, project_service: ProjectService, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("No Instructions Test Project")

    record = SpaReportGenerationService().generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
    )

    assert "User Instructions" not in record["content"]


def test_generated_report_is_retrievable_after_the_request_ends(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """Regression test: generate() used to only mutate an in-memory
    project["spa_reports"] list that was never actually persisted, so a
    report was gone the moment a fresh request re-loaded the project (the
    generate-then-immediately-view flow returned "Report not found")."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Retrievable Report Project")

    record = SpaReportGenerationService().generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
    )

    # Simulate a brand-new request: nothing about the original `project`
    # dict or the SpaReportGenerationService instance carries over.
    entries = ReportService.get_reports(project["id"])
    persisted = [e["report_data"] for e in entries if e.get("report_data")]

    assert any(item["id"] == record["id"] for item in persisted)
    found = next(item for item in persisted if item["id"] == record["id"])
    assert found["status"] == "draft"
    assert found["content"] == record["content"]

    # Marking it ready (the save-report-status flow) must also persist.
    found["status"] = "ready"
    ReportService.save_report_metadata(
        project["id"],
        found["filename"],
        report_type=found["reportType"],
        source_documents=found["sourceDocuments"],
        report_data=found,
    )

    reloaded = [
        e["report_data"]
        for e in ReportService.get_reports(project["id"])
        if e.get("report_data")
    ]
    reloaded_match = next(item for item in reloaded if item["id"] == record["id"])
    assert reloaded_match["status"] == "ready"
