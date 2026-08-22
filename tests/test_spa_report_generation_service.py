"""
Tests for free-text instructions threading through SpaReportGenerationService.
"""

from __future__ import annotations

from services.project_service import ProjectService
from services.report_plan_service import RankedFinding, ReportPlan
from services.report_service import ReportService
from services.spa_report_generation_service import (
    SpaReportGenerationService,
    _clip,
    _strip_wrapping_code_fence,
    period_by_id,
    template_by_id,
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


def test_clip_preserves_table_row_newlines_while_collapsing_prose():
    """Regression test: this module's local _clip() (used by
    _gather_sources_legacy(), among other call sites) used to collapse ALL
    whitespace including the newlines between markdown table rows, making
    tables unparseable by report_markdown_renderer.parse_markdown_blocks()
    downstream — silently defeating quantitative_analysis_service's table
    detection for the legacy-fallback source-gathering path. Mirrors the
    equivalent test in test_report_retrieval_service.py."""

    text = (
        "  Some   messy \n prose   with\nline   wraps.\n\n"
        "| Year | Gross Premium |\n"
        "|------|---------------:|\n"
        "| 2022 | 789.6 |\n"
        "| 2023 | 1,043.1 |\n"
        "| 2024 | 1,558.7 |\n"
        "\nMore   trailing    prose.\n"
    )

    clipped = _clip(text, limit=10_000)

    table_lines = [line for line in clipped.splitlines() if line.strip().startswith("|")]
    assert table_lines == [
        "| Year | Gross Premium |",
        "|------|---------------:|",
        "| 2022 | 789.6 |",
        "| 2023 | 1,043.1 |",
        "| 2024 | 1,558.7 |",
    ]
    assert "Some messy prose with line wraps." in clipped
    assert "More trailing prose." in clipped


def test_clip_still_truncates_by_length_with_ellipsis():
    clipped = _clip("word " * 100, limit=20)
    assert len(clipped) == 20
    assert clipped.endswith("…")


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


def test_gather_sources_uses_retrieval_when_available(monkeypatch):
    """When retrieve_grouped_sources returns real results, _gather_sources
    must use them directly and never fall through to the whole-document
    legacy path."""

    monkeypatch.setattr(
        "services.spa_report_generation_service.retrieve_grouped_sources",
        lambda workspace_id, queries, **kwargs: [
            {"filename": "retrieved.pdf", "excerpt": "Retrieved content"}
        ],
    )
    svc = SpaReportGenerationService()
    monkeypatch.setattr(
        svc,
        "_gather_sources_legacy",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy should not run")),
    )

    sources = svc._gather_sources(
        "ws1",
        {"documents": [{"filename": "a.pdf"}]},
        template=template_by_id("executive_summary"),
        period=period_by_id("custom"),
    )

    assert sources == [{"filename": "retrieved.pdf", "excerpt": "Retrieved content"}]


def test_gather_sources_falls_back_when_retrieval_raises(monkeypatch):
    monkeypatch.setattr(
        "services.spa_report_generation_service.retrieve_grouped_sources",
        lambda workspace_id, queries, **kwargs: (_ for _ in ()).throw(RuntimeError("Qdrant unreachable")),
    )
    svc = SpaReportGenerationService()
    sentinel = [{"filename": "legacy.pdf", "excerpt": "Legacy content"}]
    monkeypatch.setattr(svc, "_gather_sources_legacy", lambda workspace_id, docs: sentinel)

    sources = svc._gather_sources(
        "ws1",
        {"documents": [{"filename": "a.pdf"}]},
        template=template_by_id("executive_summary"),
        period=period_by_id("custom"),
    )

    assert sources == sentinel


def test_gather_sources_falls_back_when_retrieval_returns_nothing(monkeypatch):
    monkeypatch.setattr(
        "services.spa_report_generation_service.retrieve_grouped_sources",
        lambda workspace_id, queries, **kwargs: [],
    )
    svc = SpaReportGenerationService()
    sentinel = [{"filename": "legacy.pdf", "excerpt": "Legacy content"}]
    monkeypatch.setattr(svc, "_gather_sources_legacy", lambda workspace_id, docs: sentinel)

    sources = svc._gather_sources(
        "ws1",
        {"documents": [{"filename": "a.pdf"}]},
        template=template_by_id("executive_summary"),
        period=period_by_id("custom"),
    )

    assert sources == sentinel


def test_gather_sources_skips_retrieval_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "services.spa_report_generation_service.REPORT_RETRIEVAL_ENABLED", False
    )
    monkeypatch.setattr(
        "services.spa_report_generation_service.retrieve_grouped_sources",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("retrieval should not run when disabled")
        ),
    )
    svc = SpaReportGenerationService()
    sentinel = [{"filename": "legacy.pdf", "excerpt": "Legacy content"}]
    monkeypatch.setattr(svc, "_gather_sources_legacy", lambda workspace_id, docs: sentinel)

    sources = svc._gather_sources(
        "ws1",
        {"documents": [{"filename": "a.pdf"}]},
        template=template_by_id("executive_summary"),
        period=period_by_id("custom"),
    )

    assert sources == sentinel


def test_gather_sources_returns_empty_immediately_for_zero_documents(monkeypatch):
    monkeypatch.setattr(
        "services.spa_report_generation_service.retrieve_grouped_sources",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("retrieval should not run with no documents")
        ),
    )
    svc = SpaReportGenerationService()

    sources = svc._gather_sources(
        "ws1",
        {"documents": []},
        template=template_by_id("executive_summary"),
        period=period_by_id("custom"),
    )

    assert sources == []


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


class _FakeChatCompletion:
    """Captures the prompt sent to chat.completions.create() and returns a
    canned response, so tests can inspect real prompt construction without
    needing an OPENAI_API_KEY or hitting the network."""

    def __init__(self, response_text: str = "## Executive Summary\nOK.\n"):
        self.response_text = response_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        class _Choice:
            def __init__(self, content: str):
                self.message = type("Msg", (), {"content": content})()

        class _Response:
            def __init__(self, content: str):
                self.choices = [_Choice(content)]

        return _Response(self.response_text)


def _fake_openai_client(response_text: str = "## Executive Summary\nOK.\n"):
    completions = _FakeChatCompletion(response_text)
    chat = type("Chat", (), {"completions": completions})()
    client = type("Client", (), {"chat": chat})()
    return client, completions


def _seed_report(
    project_id: str,
    *,
    name: str,
    template_id: str,
    created_at: str,
    content: str,
    report_id: str | None = None,
    period_id: str = "custom",
) -> dict:
    """Write a saved SPA-shaped report directly (bypassing generate()) so
    tests can control createdAt/templateId/periodId precisely."""

    saved = ReportService.save_report(
        project_id, name, report_text=content, source_documents=[]
    )
    record = {
        "id": report_id or f"rpt_{name}",
        "filename": saved["filename"],
        "name": name,
        "path": saved["path"],
        "size": saved["size"],
        "createdAt": created_at,
        "updatedAt": created_at,
        "reportType": name,
        "templateId": template_id,
        "periodId": period_id,
        "periodName": "Custom / Ad hoc",
        "status": "draft",
        "content": content,
        "sourceDocuments": [],
        "instructions": None,
    }
    ReportService.save_report_metadata(
        project_id,
        saved["filename"],
        report_type=name,
        source_documents=[],
        report_data=record,
    )
    return record


def test_find_previous_report_matches_same_template_id_only(
    isolated_env, project_service: ProjectService
):
    # Named period ("quarterly"), not "custom" — Phase 3 Step 2 makes
    # "custom" (ad-hoc) never auto-match at all (see the dedicated
    # test_find_previous_report_never_matches_for_custom_period below);
    # this test exercises template_id matching specifically, which is
    # orthogonal and belongs on a named period.
    project = project_service.create_project("Template Match Test Project")
    _seed_report(
        project["id"],
        name="Other Template Report",
        template_id="risk_assessment",
        created_at="2026-01-01T00:00:00+00:00",
        content="Risk content.",
        period_id="quarterly",
    )
    matching = _seed_report(
        project["id"],
        name="Executive Summary Report",
        template_id="executive_summary",
        created_at="2026-01-02T00:00:00+00:00",
        content="Exec content.",
        period_id="quarterly",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "quarterly"
    )

    assert found is not None
    assert found["id"] == matching["id"]


def test_find_previous_report_matches_same_period_id_only(
    isolated_env, project_service: ProjectService
):
    """Regression test: without period_id matching, a Weekly report's
    'previous report' comparison could silently pick up the last
    Quarterly report of the same template instead of the last Weekly one."""

    project = project_service.create_project("Period Match Test Project")
    _seed_report(
        project["id"],
        name="Quarterly Report",
        template_id="executive_summary",
        created_at="2026-01-02T00:00:00+00:00",
        content="Quarterly content.",
        period_id="quarterly",
    )
    matching = _seed_report(
        project["id"],
        name="Weekly Report",
        template_id="executive_summary",
        created_at="2026-01-01T00:00:00+00:00",
        content="Weekly content.",
        period_id="weekly",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "weekly"
    )

    assert found is not None
    assert found["id"] == matching["id"]


def test_find_previous_report_returns_most_recent_by_created_at_field(
    isolated_env, project_service: ProjectService
):
    """Ordering must use report_data['createdAt'], not save order and not
    ReportService.get_reports()'s outer (call-time-computed) 'created_at'."""

    project = project_service.create_project("Ordering Test Project")
    # Saved FIRST but stamped with the LATER createdAt.
    later = _seed_report(
        project["id"],
        name="Later Report Saved First",
        template_id="executive_summary",
        created_at="2026-06-01T00:00:00+00:00",
        content="Later content.",
        period_id="quarterly",
    )
    # Saved SECOND but stamped with the EARLIER createdAt.
    _seed_report(
        project["id"],
        name="Earlier Report Saved Second",
        template_id="executive_summary",
        created_at="2026-01-01T00:00:00+00:00",
        content="Earlier content.",
        period_id="quarterly",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "quarterly"
    )

    assert found is not None
    assert found["id"] == later["id"]


def test_find_previous_report_skips_legacy_reports_without_report_data(
    isolated_env, project_service: ProjectService
):
    project = project_service.create_project("Legacy Skip Test Project")
    # A legacy/non-SPA report: no source_documents means save_report()
    # never writes a report_data sidecar at all.
    ReportService.save_report(
        project["id"],
        "Legacy Streamlit Report",
        report_text="Old content.",
    )
    valid = _seed_report(
        project["id"],
        name="Valid SPA Report",
        template_id="executive_summary",
        created_at="2026-01-01T00:00:00+00:00",
        content="Valid content.",
        period_id="quarterly",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "quarterly"
    )

    assert found is not None
    assert found["id"] == valid["id"]


def test_find_previous_report_skips_malformed_report_data(
    isolated_env, project_service: ProjectService
):
    project = project_service.create_project("Malformed Skip Test Project")
    saved = ReportService.save_report(
        project["id"],
        "Malformed Report",
        report_text="Some content.",
        source_documents=[],
    )
    # report_data present but missing createdAt/content.
    ReportService.save_report_metadata(
        project["id"],
        saved["filename"],
        report_type="Malformed Report",
        source_documents=[],
        report_data={"id": "rpt_malformed", "templateId": "executive_summary"},
    )
    valid = _seed_report(
        project["id"],
        name="Valid SPA Report",
        template_id="executive_summary",
        created_at="2026-01-01T00:00:00+00:00",
        content="Valid content.",
        period_id="quarterly",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "quarterly"
    )

    assert found is not None
    assert found["id"] == valid["id"]


def test_find_previous_report_returns_none_when_nothing_matches(
    isolated_env, project_service: ProjectService
):
    project = project_service.create_project("No Match Test Project")
    _seed_report(
        project["id"],
        name="Different Template Report",
        template_id="risk_assessment",
        created_at="2026-01-01T00:00:00+00:00",
        content="Content.",
        period_id="quarterly",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "quarterly"
    )

    assert found is None


def test_find_previous_report_never_matches_for_custom_period(
    isolated_env, project_service: ProjectService
):
    """Phase 3 Step 2: every ad-hoc/"Custom" report shares the single
    generic period_id "custom" with no real date-range differentiation —
    a previous ad-hoc report might cover a completely unrelated scope, so
    "Changes Since Last Report" must never be offered for a custom-period
    report, even when a same-template, same-period-id previous report
    genuinely exists."""

    project = project_service.create_project("Custom Period Never Matches Project")
    _seed_report(
        project["id"],
        name="Earlier Ad Hoc Report",
        template_id="executive_summary",
        created_at="2026-01-01T00:00:00+00:00",
        content="Earlier content.",
        period_id="custom",
    )

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "custom"
    )

    assert found is None


def test_find_previous_report_returns_none_for_empty_workspace(
    isolated_env, project_service: ProjectService
):
    project = project_service.create_project("Empty Workspace Test Project")

    found = SpaReportGenerationService()._find_previous_report(
        project["id"], "executive_summary", "custom"
    )

    assert found is None


def test_generate_markdown_prompt_unchanged_when_no_previous_report():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt_without_param = completions.calls[0]["messages"][1]["content"]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        previous_report=None,
    )
    prompt_with_explicit_none = completions.calls[1]["messages"][1]["content"]

    assert prompt_without_param == prompt_with_explicit_none
    assert "Changes Since Last Report" not in prompt_without_param


def test_generate_markdown_requires_fact_analysis_implication_and_basis_tag():
    """Step B: Key Findings must move FACT -> ANALYSIS -> IMPLICATION and
    every finding must be tagged with its evidentiary basis, distinguishing
    a stated source fact from a calculated result from an inference."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "FACT" in prompt and "ANALYSIS" in prompt and "IMPLICATION" in prompt
    assert "`Source fact`" in prompt and "`Calculated result`" in prompt and "`Analytical inference`" in prompt
    assert "not a paraphrase" in prompt
    assert "never present an inference as if it were a stated fact" in prompt


def test_generate_markdown_requires_evidence_tags_on_their_own_separate_lines():
    """Report Output Quality Upgrade Step A: Basis/Confidence/Source must
    each be required on their own line, never appended to the finding's
    prose — this is what a real generated report was found to violate,
    causing evidence metadata to run together with the narrative text."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "on their OWN separate lines" in prompt
    assert "on its own line" in prompt
    assert "never fold them into the same sentence or line" in prompt


def test_generate_markdown_prohibits_cagr_mislabeling():
    """Report Output Quality Upgrade Step E: a real generated report
    called a single-period 2023-to-2024 year-over-year growth figure a
    'compounded annual growth rate' — nothing in the pipeline computes a
    true CAGR, so the prompt must explicitly forbid the term for
    anything but a genuinely multi-period compounded rate."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "CAGR" in prompt and "compound annual growth rate" in prompt
    assert "never use either term for a single period-over-period change" in prompt
    assert "year-over-year change" in prompt


def test_generate_markdown_names_every_source_document_regardless_of_relevance():
    """Document Coverage fix: reinforces that every document in `sources`
    (now guaranteed complete by the retrieval layer when the user asked
    for all documents) must be referenced — and that a lightly-relevant
    one must not be padded or have content invented for it just to
    appear more substantial."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [
        {"filename": "a.pdf", "excerpt": "Rich evidence."},
        {"filename": "b.pdf", "excerpt": "One thin point."},
    ]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "a.pdf" in prompt and "b.pdf" in prompt
    assert "must be referenced by name at least once" in prompt
    assert "does not mean forcing equal coverage" in prompt
    assert "never fabricate a finding just to make a" in prompt


def test_generate_markdown_includes_coverage_gap_note_when_a_document_could_not_be_covered():
    """Document Coverage fix (item 12/18): when a document was in scope
    but genuinely couldn't contribute evidence, the application — not the
    user — tells the model to acknowledge it plainly rather than
    silently omitting it or inventing content to compensate."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        coverage_gaps=[{"filename": "Minutes - 14th Meeting.pdf", "reason": "no_matching_evidence"}],
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "REPORT SCOPE NOTE" in prompt
    assert "Minutes - 14th Meeting.pdf" in prompt
    assert "no matching evidence" in prompt
    assert "Do not silently omit them" in prompt
    assert "do not invent findings from them" in prompt


def test_generate_markdown_omits_coverage_gap_note_when_no_gaps():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        coverage_gaps=None,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "REPORT SCOPE NOTE" not in prompt


def test_generate_markdown_instructs_restraint_against_unearned_adjectives():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "remarkable" in prompt and "robust" in prompt  # named as words to avoid
    assert "not a promoter" in prompt
    assert "does not by itself mean profitability improved" in prompt


def test_generate_markdown_includes_categorical_vs_temporal_guardrail():
    """Phase 3 Step 2: the prompt must explicitly warn against treating a
    cross-category comparison (e.g. two different channels' Premium
    Share in the same period) as a change over time — the actual
    root-cause fix for the reported 81.6%/131.0%/25.4% fabricated
    percentage-change bugs, since the deterministic layer correctly
    refuses to compute these itself but the raw categorical rows still
    reach the model."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "SAME thing at two DIFFERENT points in time" in prompt
    assert "Digital has the highest Premium Share at 38%" in prompt
    assert "cross-sectional comparison" in prompt


def test_generate_markdown_includes_causal_language_guardrail():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "unless a source document explicitly states that causal mechanism" in prompt
    assert "warrants investigation into whether service issues" in prompt


def test_generate_markdown_grounds_risks_and_opportunities_with_basis_tag():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    risks_section = prompt.split("## Risks & Issues")[1].split("## Opportunities")[0]
    opportunities_section = prompt.split("## Opportunities")[1].split("## Strategic Recommendations")[0]

    assert "never a generic category label" in risks_section
    assert "Claims backlog escalation" in risks_section
    assert "**Basis:**" in risks_section
    assert "**Basis:**" in opportunities_section


def test_generate_markdown_requires_bulleted_risks_and_opportunities():
    """Report Output Quality Upgrade Step B: Risks & Issues / Opportunities
    items must be formatted as markdown bullets so dashboard extraction can
    find them, and the 'none found' wording must distinguish 'not in the
    evidence' from the stronger, unsupported claim 'none exist'."""

    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    risks_section = prompt.split("## Risks & Issues")[1].split("## Opportunities")[0]
    opportunities_section = prompt.split("## Opportunities")[1].split("## Strategic Recommendations")[0]

    assert "its own markdown bullet" in risks_section
    assert "No risks were identified in the evidence reviewed" in risks_section
    assert "not 'no risks exist'" in risks_section

    assert "its own markdown bullet" in opportunities_section
    assert "No opportunities were identified in the evidence reviewed" in opportunities_section


def test_generate_markdown_forbids_padding_in_detailed_analysis_and_risks():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "Do not restate findings from Key Findings to lengthen this section" in prompt
    assert "rather than manufacturing a generic risk" in prompt


def test_generate_markdown_recommendations_require_action_rationale_measurement():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    recommendations_section = prompt.split("## Strategic Recommendations")[1].split("## Conclusion")[0]
    assert "`**Action:**`" in recommendations_section
    assert "`**Rationale:**`" in recommendations_section
    assert "`**Measurement:**`" in recommendations_section
    assert "never a bare instruction like 'invest in technology'" in recommendations_section
    assert "must cite a specific finding, metric, or figure" in recommendations_section


def test_generate_markdown_recommendations_trace_to_plan_when_present():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]
    plan = ReportPlan(
        ranked_findings=[
            RankedFinding(label="Gross Premium", materiality_score=97.4, direction="increase")
        ]
    )

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        report_plan=plan,
    )
    prompt = completions.calls[0]["messages"][1]["content"]
    recommendations_section = prompt.split("## Strategic Recommendations")[1].split("## Conclusion")[0]

    assert "Every recommendation must trace back to one of the ranked findings" in recommendations_section


def test_generate_markdown_recommendations_omit_plan_trace_clause_when_no_plan():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        report_plan=None,
    )
    prompt = completions.calls[0]["messages"][1]["content"]
    recommendations_section = prompt.split("## Strategic Recommendations")[1].split("## Conclusion")[0]

    assert "Every recommendation must trace back to one of the ranked findings" not in recommendations_section
    # Action/Rationale/Measurement structure still applies without a plan.
    assert "`**Action:**`" in recommendations_section


def test_generate_markdown_executive_summary_anchors_to_report_plan_when_present():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]
    plan = ReportPlan(
        ranked_findings=[
            RankedFinding(label="Gross Premium", materiality_score=97.4, direction="increase")
        ]
    )

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        report_plan=plan,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    exec_summary_section = prompt.split("## Executive Summary")[1].split("## Key Findings")[0]
    assert "Build it from the 3-5 highest-materiality items in the Report Plan above" in exec_summary_section
    assert "Do not restate sentences that will also appear in Key Findings" in prompt


def test_generate_markdown_executive_summary_omits_plan_reference_when_no_plan():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        report_plan=None,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    exec_summary_section = prompt.split("## Executive Summary")[1].split("## Key Findings")[0]
    assert "Report Plan above" not in exec_summary_section
    # The "no sentence reuse" rule still applies even without a plan.
    assert "Do not restate sentences that will also appear in Key Findings" in prompt


def test_generate_markdown_includes_changes_section_when_previous_report_present():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]
    previous_report = {
        "content": "## Executive Summary\nVendor contract was unsigned.\nRevenue: $1.2M.",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        previous_report=previous_report,
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "## Changes Since Last Report" in prompt
    assert prompt.index("## Strategic Recommendations") < prompt.index(
        "## Changes Since Last Report"
    )
    assert prompt.index("## Changes Since Last Report") < prompt.index("## Conclusion")
    assert "Vendor contract was unsigned" in prompt
    assert "Revenue: $1.2M" in prompt


def test_generate_markdown_omits_changes_section_when_previous_report_has_no_content():
    svc = SpaReportGenerationService()
    client, completions = _fake_openai_client()
    svc._client = client
    sources = [{"filename": "a.pdf", "excerpt": "Some evidence."}]

    svc._generate_markdown(
        title="Test Report",
        period_name="Custom / Ad hoc",
        template_name="Executive Summary",
        sources=sources,
        previous_report={"content": "", "createdAt": "2026-01-01T00:00:00+00:00"},
    )
    prompt = completions.calls[0]["messages"][1]["content"]

    assert "Changes Since Last Report" not in prompt


def test_generate_wires_previous_report_lookup_across_calls(
    isolated_env, project_service: ProjectService, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Wiring Test Project")

    first = SpaReportGenerationService().generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
    )

    calls: list[tuple[str, str, str]] = []
    svc = SpaReportGenerationService()
    original = svc._find_previous_report

    def _spy(workspace_id, template_id, period_id):
        calls.append((workspace_id, template_id, period_id))
        return original(workspace_id, template_id, period_id)

    monkeypatch.setattr(svc, "_find_previous_report", _spy)

    second = svc.generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
    )

    assert calls == [(project["id"], "executive_summary", "custom")]
    assert second["id"] != first["id"]


def test_generate_embeds_chart_block_for_quantitative_content(
    isolated_env, project_service: ProjectService
):
    """Reports whose narrative contains real quantitative data (a numeric
    table, currency figures) must get an auto-generated chart block
    embedded in record['content'] — the exact field export_report() reads
    at export time — even for a report type ("Executive Summary") that the
    visualization engine's report-type-name confidence scoring alone would
    never mark HIGH confidence for."""

    project = project_service.create_project("Chartable Report Project")
    chartable_markdown = (
        "## Executive Summary\n"
        "Quarterly revenue grew steadily across the year.\n\n"
        "## Key Findings\n\n"
        "### Revenue by Quarter\n\n"
        "| Quarter | Revenue |\n"
        "|---------|---------|\n"
        "| Q1 | $1,200,000 |\n"
        "| Q2 | $1,450,000 |\n"
        "| Q3 | $1,600,000 |\n"
        "| Q4 | $1,900,000 |\n\n"
        "**Confidence:** High — figures drawn directly from the financial statements.  \n"
        "**Source:** financials.pdf\n\n"
        "## Conclusion\n"
        "Revenue trended upward each quarter.\n"
    )

    svc = SpaReportGenerationService()
    svc._generate_markdown = lambda **kwargs: chartable_markdown

    record = svc.generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="quarterly",
    )

    assert "<!-- REPORT_CHARTS" in record["content"]


def test_generate_omits_visible_charts_for_purely_narrative_content(
    isolated_env, project_service: ProjectService, monkeypatch
):
    """A report with no chartable data (the no-OPENAI_API_KEY fallback
    markdown, which is boilerplate prose with no figures) must not produce
    any chart visuals at export time. The engine still embeds a metadata
    audit trail (visualization_decision, _suppress_theme_charts=True) even
    when nothing is chartable — that's harmless bookkeeping invisible in
    the UI and ignored by exports — so the real assertion is has_chart_
    visuals(), the exact check export_chart_blocks.py uses to decide
    whether to render anything, not raw-string presence of the block."""

    from services.report_chart_data import extract_chart_data
    from services.report_chart_figures import has_chart_visuals

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Narrative Only Report Project")

    record = SpaReportGenerationService().generate(
        workspace_id=project["id"],
        project=project,
        template_id="executive_summary",
        period_id="custom",
    )

    chart_data = extract_chart_data(record["content"])
    assert not has_chart_visuals(chart_data)
