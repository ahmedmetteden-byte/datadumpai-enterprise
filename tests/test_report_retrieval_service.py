"""
Unit tests for retrieval-grounded report source selection — pure logic,
no real OpenAI/Qdrant calls (fake embedder/qdrant test doubles).
"""

from __future__ import annotations

from services.report_retrieval_service import (
    FACETS,
    _clip,
    build_facet_queries,
    compute_coverage_gaps,
    detect_all_documents_intent,
    retrieve_grouped_sources,
)


def test_build_facet_queries_includes_one_query_per_facet():
    queries = build_facet_queries(
        template_name="Executive Summary",
        template_description="Concise leadership brief.",
        period_name="Monthly Report",
    )
    assert len(queries) == len(FACETS)
    for query in queries:
        assert "Executive Summary" in query
        assert "Monthly Report" in query


def test_build_facet_queries_adds_instructions_as_its_own_query():
    queries = build_facet_queries(
        template_name="Executive Summary",
        template_description="Concise leadership brief.",
        period_name="Monthly Report",
        instructions="Focus only on Q3 sales",
    )
    assert len(queries) == len(FACETS) + 1
    assert queries[-1] == "Focus only on Q3 sales"
    assert all("Q3 sales" in query for query in queries[:-1])


class _FakeEmbedder:
    """Returns one distinct 1-dimensional vector per input text, in order,
    so _FakeQdrant below can recover which query a search call came from."""

    def embed_texts(self, texts, *, batch_size: int = 64):
        return [[float(index)] for index in range(len(texts))]


class _FakeQdrant:
    def __init__(
        self,
        hits_by_query_index: dict[int, list[dict]],
        hits_by_document_id: dict[str, list[dict]] | None = None,
    ):
        self._hits_by_query_index = hits_by_query_index
        self._hits_by_document_id = hits_by_document_id or {}
        self.calls = 0
        self.document_id_calls: list[str] = []

    def search(self, *, workspace_id, query_vector, limit, document_id=None):
        self.calls += 1
        if document_id is not None:
            self.document_id_calls.append(document_id)
            return self._hits_by_document_id.get(document_id, [])
        index = int(query_vector[0])
        return self._hits_by_query_index.get(index, [])


def _hit(id_, score, document_id, filename, chunk_index, text):
    return {
        "id": id_,
        "score": score,
        "document_id": document_id,
        "filename": filename,
        "chunk_index": chunk_index,
        "heading": "",
        "text": text,
    }


def test_retrieve_grouped_sources_returns_empty_when_no_hits():
    result = retrieve_grouped_sources(
        "ws1", ["q1", "q2"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant({})
    )
    assert result == []


def test_retrieve_grouped_sources_returns_empty_for_no_queries():
    result = retrieve_grouped_sources(
        "ws1", [], embedder=_FakeEmbedder(), qdrant=_FakeQdrant({})
    )
    assert result == []


def test_retrieve_grouped_sources_ranks_documents_by_best_score():
    hits = {
        0: [
            _hit("c1", 0.9, "doc-a", "a.pdf", 0, "Doc A chunk 0"),
            _hit("c2", 0.3, "doc-b", "b.pdf", 0, "Doc B chunk 0"),
        ],
    }
    result = retrieve_grouped_sources(
        "ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert [source["filename"] for source in result] == ["a.pdf", "b.pdf"]


def test_retrieve_grouped_sources_reorders_selected_chunks_by_reading_position():
    """A high-scoring chunk near the end of a document (high chunk_index)
    must still be selected — this is what fixes 'relevant info near the
    end of a large document' — but reassembled in reading order, with a
    gap marker for the skipped middle, not shuffled by score."""

    hits = {
        0: [
            _hit("c1", 0.4, "doc-a", "a.pdf", 0, "Beginning of the document."),
            _hit("c2", 0.95, "doc-a", "a.pdf", 9, "Important finding near the end."),
        ],
    }
    result = retrieve_grouped_sources(
        "ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert len(result) == 1
    excerpt = result[0]["excerpt"]
    assert excerpt.index("Beginning of the document.") < excerpt.index(
        "Important finding near the end."
    )
    assert "[…]" in excerpt


def test_retrieve_grouped_sources_merges_duplicate_chunk_ids_keeping_best_score():
    hits = {
        0: [_hit("shared", 0.4, "doc-a", "a.pdf", 0, "Shared chunk text")],
        1: [_hit("shared", 0.9, "doc-a", "a.pdf", 0, "Shared chunk text")],
    }
    result = retrieve_grouped_sources(
        "ws1", ["q1", "q2"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert len(result) == 1
    assert result[0]["excerpt"].count("Shared chunk text") == 1


def test_retrieve_grouped_sources_caps_documents_and_chunks_per_document(monkeypatch):
    monkeypatch.setattr("services.report_retrieval_service.MAX_DOCUMENTS", 2)
    monkeypatch.setattr("services.report_retrieval_service.MAX_CHUNKS_PER_DOCUMENT", 1)
    hits = {
        0: [
            _hit("c1", 0.9, "doc-a", "a.pdf", 0, "A chunk 1"),
            _hit("c2", 0.8, "doc-a", "a.pdf", 1, "A chunk 2"),
            _hit("c3", 0.7, "doc-b", "b.pdf", 0, "B chunk"),
            _hit("c4", 0.6, "doc-c", "c.pdf", 0, "C chunk"),
        ],
    }
    result = retrieve_grouped_sources(
        "ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert [source["filename"] for source in result] == ["a.pdf", "b.pdf"]
    assert result[0]["excerpt"] == "A chunk 1"


def test_retrieve_grouped_sources_excludes_documents_below_relevance_floor(monkeypatch):
    """Phase D: confirmed against real data — a genuinely irrelevant
    document (an HR policy doc mixed into a financial report request)
    scored 0.24-0.27 across every facet query, while the report's real
    source documents scored 0.36-0.51 on the same facets. Before this
    floor existed, the rank+cap scheme had nothing that excluded a
    document purely for being irrelevant — with fewer documents than
    MAX_DOCUMENTS, everything survived regardless of score."""

    monkeypatch.setattr("services.report_retrieval_service.MIN_DOCUMENT_RELEVANCE_SCORE", 0.30)
    hits = {
        0: [
            _hit("c1", 0.4, "doc-a", "relevant.pdf", 0, "Relevant chunk"),
            _hit("c2", 0.25, "doc-b", "irrelevant.pdf", 0, "Irrelevant chunk"),
        ],
    }
    result = retrieve_grouped_sources(
        "ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert [source["filename"] for source in result] == ["relevant.pdf"]


def test_retrieve_grouped_sources_relevance_floor_does_not_apply_to_coverage_stage(monkeypatch):
    """A document explicitly guaranteed via the "use every document"
    coverage stage must still be included even if its score is below the
    relevance floor — a user who asked for every document to be used has
    already overridden relevance as the inclusion criterion."""

    monkeypatch.setattr("services.report_retrieval_service.MIN_DOCUMENT_RELEVANCE_SCORE", 0.30)
    hits_by_query = {0: [_hit("c1", 0.9, "doc-a-id", "a.pdf", 0, "A chunk")]}
    hits_by_document = {
        "doc-b-id": [_hit("c2", 0.1, "doc-b-id", "b.pdf", 0, "Low-scoring but explicitly requested")],
    }
    qdrant = _FakeQdrant(hits_by_query, hits_by_document)
    documents = [
        {"id": "doc-a-id", "filename": "a.pdf", "status": "indexed"},
        {"id": "doc-b-id", "filename": "b.pdf", "status": "indexed"},
    ]
    result = retrieve_grouped_sources(
        "ws1", ["q1"], embedder=_FakeEmbedder(), qdrant=qdrant, documents=documents
    )
    assert {source["filename"] for source in result} == {"a.pdf", "b.pdf"}


def test_retrieve_grouped_sources_deduplicates_identical_content_under_different_filenames():
    """Phase D: confirmed against real data — the same document indexed
    twice under two filenames (e.g. an accidental re-upload) was being
    presented as two independent corroborating sources, inflating stated
    confidence and citation count for what is really one source counted
    twice. Only the first-ranked copy should survive."""

    hits = {
        0: [
            _hit("c1", 0.9, "doc-a", "January_2026_Monthly_Report.docx", 0, "Same content"),
            _hit("c2", 0.85, "doc-b", "January_2026_Monthly_Report_copy.docx", 0, "Same content"),
        ],
    }
    result = retrieve_grouped_sources(
        "ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert [source["filename"] for source in result] == ["January_2026_Monthly_Report.docx"]


def test_clip_preserves_table_row_newlines_while_collapsing_prose():
    """Regression test for the bug that silently defeated Step 1's
    quantitative analysis: _clip() used to collapse ALL whitespace,
    including the newlines between a markdown table's rows, making the
    table unparseable by report_markdown_renderer.parse_markdown_blocks()
    downstream. Table rows must survive clipping intact; surrounding prose
    should still have its whitespace normalized as before."""

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


def test_detect_all_documents_intent_matches_spec_examples():
    """Document Coverage fix: matches every phrasing given as an example
    in the spec, plus the exact real-world prompt that triggered the
    original bug."""

    positives = [
        "Combine all documents.",
        "Produce a comprehensive report from all uploaded documents.",
        "Analyze everything in this workspace.",
        "Review all four documents.",
        "Prepare a report using all the documents.",
        "Produce a comprehensive report by combining all four documents uploaded in this workspace.",
    ]
    for instructions in positives:
        assert detect_all_documents_intent(instructions) is True, instructions


def test_detect_all_documents_intent_ignores_targeted_and_empty_instructions():
    negatives = [
        None,
        "",
        "   ",
        "What are the claims issues?",
        "Summarize the annual report.",
        "Use documents A, B and C only.",
    ]
    for instructions in negatives:
        assert detect_all_documents_intent(instructions) is False, instructions


def test_compute_coverage_gaps_returns_empty_when_all_covered():
    sources = [{"filename": "a.pdf", "excerpt": "x"}, {"filename": "b.pdf", "excerpt": "y"}]
    documents = [{"filename": "a.pdf", "status": "indexed"}, {"filename": "b.pdf", "status": "indexed"}]
    assert compute_coverage_gaps(sources, documents) == []


def test_compute_coverage_gaps_classifies_missing_documents_by_status():
    sources = [{"filename": "a.pdf", "excerpt": "x"}]
    documents = [
        {"filename": "a.pdf", "status": "indexed"},
        {"filename": "failed.pdf", "status": "failed"},
        {"filename": "sparse.pdf", "status": "indexed"},
        {"filename": "still-processing.pdf", "status": "processing"},
    ]
    gaps = compute_coverage_gaps(sources, documents)
    by_filename = {gap["filename"]: gap["reason"] for gap in gaps}
    assert by_filename == {
        "failed.pdf": "processing_failed",
        "sparse.pdf": "no_matching_evidence",
        "still-processing.pdf": "not_yet_indexed",
    }


def test_retrieve_grouped_sources_without_documents_param_is_unchanged():
    """Backward compatibility: omitting `documents` (every existing
    caller before this fix) must behave exactly as before — no coverage
    stage, no extra Qdrant calls."""

    hits = {0: [_hit("c1", 0.9, "doc-a", "a.pdf", 0, "A chunk")]}
    qdrant = _FakeQdrant(hits)
    result = retrieve_grouped_sources("ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=qdrant)
    assert [source["filename"] for source in result] == ["a.pdf"]
    assert qdrant.document_id_calls == []


def test_retrieve_grouped_sources_covers_a_document_missed_by_global_retrieval():
    """The exact real-world regression: a document with real, successfully-
    indexed chunks that never surfaces in ANY facet query's top-K must
    still end up in the final sources list when the caller passes the
    workspace's document list (signaling "all documents" intent was
    detected)."""

    hits_by_query = {
        0: [_hit("c1", 0.9, "doc-a-id", "a.pdf", 0, "A chunk")],
        1: [_hit("c1", 0.9, "doc-a-id", "a.pdf", 0, "A chunk")],
    }
    hits_by_document = {
        "doc-b-id": [_hit("c2", 0.5, "doc-b-id", "b.pdf", 0, "B chunk never in global top-K")],
    }
    qdrant = _FakeQdrant(hits_by_query, hits_by_document)
    documents = [
        {"id": "doc-a-id", "filename": "a.pdf", "status": "indexed"},
        {"id": "doc-b-id", "filename": "b.pdf", "status": "indexed"},
    ]

    result = retrieve_grouped_sources(
        "ws1", ["q1", "q2"], embedder=_FakeEmbedder(), qdrant=qdrant, documents=documents
    )

    filenames = {source["filename"] for source in result}
    assert filenames == {"a.pdf", "b.pdf"}
    assert "B chunk never in global top-K" in next(
        s["excerpt"] for s in result if s["filename"] == "b.pdf"
    )
    # The coverage query was scoped to the specific missing document.
    assert "doc-b-id" in qdrant.document_id_calls
    assert "doc-a-id" not in qdrant.document_id_calls  # already covered, no extra query needed


def test_retrieve_grouped_sources_coverage_skips_unindexed_documents():
    """A document that failed to index (or is still processing) has no
    chunks the retrieval layer could possibly recover — that's a
    compute_coverage_gaps() reporting concern, not something this stage
    should attempt (and silently produce nothing for)."""

    hits_by_query = {0: [_hit("c1", 0.9, "doc-a-id", "a.pdf", 0, "A chunk")]}
    qdrant = _FakeQdrant(hits_by_query, {})
    documents = [
        {"id": "doc-a-id", "filename": "a.pdf", "status": "indexed"},
        {"id": "doc-b-id", "filename": "b.pdf", "status": "failed"},
    ]

    result = retrieve_grouped_sources(
        "ws1", ["q1"], embedder=_FakeEmbedder(), qdrant=qdrant, documents=documents
    )

    assert [s["filename"] for s in result] == ["a.pdf"]
    assert qdrant.document_id_calls == []


def test_retrieve_grouped_sources_excerpt_preserves_table_structure_when_clipped():
    """End-to-end (through retrieve_grouped_sources, not just _clip directly):
    a hit whose text contains a real markdown table must come back with the
    table's rows still newline-separated, not collapsed onto one line."""

    table_text = (
        "Some narrative text about the report.\n\n"
        "| Year | Gross Premium |\n"
        "|------|---------------:|\n"
        "| 2022 | 789.6 |\n"
        "| 2023 | 1,043.1 |\n"
        "| 2024 | 1,558.7 |\n"
    )
    hits = {
        0: [_hit("c1", 0.9, "doc-a", "a.xlsx", 0, table_text)],
    }
    result = retrieve_grouped_sources(
        "ws1", ["only query"], embedder=_FakeEmbedder(), qdrant=_FakeQdrant(hits)
    )
    assert len(result) == 1
    excerpt = result[0]["excerpt"]
    table_lines = [line for line in excerpt.splitlines() if line.strip().startswith("|")]
    assert table_lines == [
        "| Year | Gross Premium |",
        "|------|---------------:|",
        "| 2022 | 789.6 |",
        "| 2023 | 1,043.1 |",
        "| 2024 | 1,558.7 |",
    ]
