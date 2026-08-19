"""
Unit tests for retrieval-grounded report source selection — pure logic,
no real OpenAI/Qdrant calls (fake embedder/qdrant test doubles).
"""

from __future__ import annotations

from services.report_retrieval_service import (
    FACETS,
    _clip,
    build_facet_queries,
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
    def __init__(self, hits_by_query_index: dict[int, list[dict]]):
        self._hits_by_query_index = hits_by_query_index
        self.calls = 0

    def search(self, *, workspace_id, query_vector, limit):
        self.calls += 1
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
