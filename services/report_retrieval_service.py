"""
Retrieval-grounded source selection for AI report generation.

Reuses the same Qdrant/embedding infrastructure Intelligence Studio's RAG
already uses (services/intelligence_rag_service.py) to select the most
relevant document chunks for a report request, instead of naively reading
a project's first N documents. This module only selects and assembles
source material — it feeds the existing report-writing prompt in
services/spa_report_generation_service.py, it does not write the report.
"""

from __future__ import annotations

import os
import re
from typing import Any

from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService

# Tunable without a code change — see the approved plan for defaults/rationale.
FACET_TOP_K = int(os.getenv("REPORT_RETRIEVAL_FACET_TOP_K", "12"))
MAX_CHUNKS_PER_DOCUMENT = int(os.getenv("REPORT_RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT", "6"))
MAX_DOCUMENTS = int(os.getenv("REPORT_RETRIEVAL_MAX_DOCUMENTS", "14"))
PER_DOCUMENT_CHAR_CAP = int(os.getenv("REPORT_RETRIEVAL_PER_DOCUMENT_CHAR_CAP", "4500"))
TOTAL_BUDGET_CHARS = int(os.getenv("REPORT_RETRIEVAL_TOTAL_BUDGET_CHARS", "60000"))

# Phase D: the rank+cap scheme above has no floor — with fewer than
# MAX_DOCUMENTS documents in a workspace, EVERY document survives into the
# report's evidence regardless of how irrelevant it is to the facet
# queries, because nothing before the cap ever asks "is this actually
# relevant" rather than just "is this the best of what's here". Confirmed
# against real data: a genuinely unrelated HR-policy document scored
# 0.24-0.27 cosine similarity across every facet query for a financial
# report, while the report's own real source documents scored 0.36-0.51
# on the same facets — a wide, consistent gap. This floor is set well
# below the observed relevant range and well above the observed
# irrelevant range, with margin on both sides. Applies ONLY to the
# global relevance-ranking stage below, never to _ensure_document_
# coverage()'s explicit, opt-in "use every document" guarantee — a user
# who asks for every document to be used has already overridden
# relevance as the inclusion criterion.
MIN_DOCUMENT_RELEVANCE_SCORE = float(os.getenv("REPORT_RETRIEVAL_MIN_DOCUMENT_RELEVANCE_SCORE", "0.30"))

# One query per report facet rather than a single query — a single query
# biases retrieval toward whichever theme it best matches, reproducing the
# "clustered from one document" problem the report prompt already warns
# against. Each facet is combined with the report's own context below.
FACETS: tuple[str, ...] = (
    "overall summary and headline situation",
    "key findings, results, metrics, and outcomes",
    "risks, issues, problems, and concerns",
    "opportunities and positive developments",
    "recommended next steps and action items",
)


_ALL_DOCUMENTS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\ball\b[^.!?\n]{0,25}\bdocuments?\b", re.IGNORECASE),
    re.compile(r"\ball\b[^.!?\n]{0,25}\buploaded\b", re.IGNORECASE),
    re.compile(r"\bevery\b[^.!?\n]{0,25}\bdocuments?\b", re.IGNORECASE),
    re.compile(r"\beverything\b[^.!?\n]{0,25}\bworkspace\b", re.IGNORECASE),
    re.compile(r"\bcombin(?:e|ing)\b[^.!?\n]{0,25}\ball\b", re.IGNORECASE),
    re.compile(r"\bentire\b[^.!?\n]{0,25}\bworkspace\b", re.IGNORECASE),
)


def detect_all_documents_intent(instructions: str | None) -> bool:
    """Deterministic (not LLM-based) detection of an explicit "use every
    document" request — e.g. "Combine all documents," "Analyze everything
    in this workspace," "Review all four documents." Intentionally
    permissive: a false positive just means a few extra per-document
    coverage queries run for documents that would likely have been
    included anyway; a false negative means a document silently
    disappears from a report the user explicitly asked to cover
    completely, which is the actual failure mode this exists to prevent."""

    if not instructions or not instructions.strip():
        return False

    text = instructions.strip()
    return any(pattern.search(text) for pattern in _ALL_DOCUMENTS_PATTERNS)


def build_facet_queries(
    *,
    template_name: str,
    template_description: str,
    period_name: str,
    instructions: str | None = None,
) -> list[str]:
    """Build one retrieval query per report facet, plus the user's raw
    instructions as their own query when given (often the most specific
    signal available). The reporting period is folded into the query text
    as a soft semantic signal rather than a rigid date filter — chunk
    payloads carry no date metadata, and a document indexed in August can
    describe a July event, so a hard filter would silently drop it."""

    context = f"{template_name} — {template_description}. Reporting period: {period_name}."
    if instructions and instructions.strip():
        context += f" User instruction: {instructions.strip()}"

    queries = [f"{context} Focus: {facet}." for facet in FACETS]
    if instructions and instructions.strip():
        queries.append(instructions.strip())
    return queries


_TABLE_ROW = re.compile(r"^\|.*\|$")


def _clip(text: str, limit: int) -> str:
    """Collapse whitespace to normalize messy extraction artifacts (PDF
    line-wraps, repeated spaces) while preserving markdown table
    structure — collapsing a table's one-row-per-line layout onto a
    single line makes it unparseable by report_markdown_renderer.
    parse_markdown_blocks(), which quantitative_analysis_service.py
    depends on to find real tables in retrieved evidence."""

    segments: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        kind = "table" if _TABLE_ROW.match(line.strip()) else "prose"
        if segments and segments[-1][0] == kind:
            segments[-1][1].append(line)
        else:
            segments.append((kind, [line]))

    rendered: list[str] = []
    for kind, lines in segments:
        if kind == "table":
            rendered.append("\n".join(line.strip() for line in lines))
        else:
            collapsed = re.sub(r"\s+", " ", " ".join(lines)).strip()
            if collapsed:
                rendered.append(collapsed)

    cleaned = "\n\n".join(rendered).strip()

    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _assemble_excerpt(hits: list[dict[str, Any]], *, budget: int) -> str:
    """Pick a document's top-scoring chunks, reassemble them in original
    reading order (selection is relevance-driven, but shuffled fragments
    would read as incoherent), and clip to the given character budget.
    Shared by the global-relevance loop and the per-document coverage
    query below so both build excerpts identically."""

    selected = sorted(hits, key=lambda hit: hit["score"], reverse=True)[:MAX_CHUNKS_PER_DOCUMENT]
    selected.sort(key=lambda hit: hit["chunk_index"])

    parts: list[str] = []
    previous_index: int | None = None
    for hit in selected:
        if previous_index is not None and hit["chunk_index"] > previous_index + 1:
            parts.append("[…]")
        parts.append(str(hit["text"]))
        previous_index = hit["chunk_index"]

    return _clip("\n\n".join(parts), min(PER_DOCUMENT_CHAR_CAP, budget))


def _ensure_document_coverage(
    sources: list[dict[str, str]],
    *,
    documents: list[dict[str, Any]],
    vectors: list[list[float]],
    workspace_id: str,
    qdrant: QdrantService,
    remaining_budget: int,
) -> list[dict[str, str]]:
    """Guarantee every successfully-indexed workspace document contributes
    at least some evidence — used only when the caller has detected an
    explicit "use every document" instruction. A document only reaches
    this stage if the global facet retrieval above never surfaced any of
    its chunks in any query's top-K; this issues one additional,
    document-scoped Qdrant query per still-missing document (still
    relevance-ranked within that document, still capped at
    MAX_CHUNKS_PER_DOCUMENT — never "send the whole document"), reusing
    the same query vectors already embedded for the global pass so no
    extra embedding calls are made."""

    covered = {source["filename"] for source in sources}
    supplemented = list(sources)

    for document in documents:
        if remaining_budget <= 0:
            break

        filename = str(document.get("filename") or "")
        document_id = str(document.get("id") or "")

        if not filename or filename in covered:
            continue
        if document.get("status") != "indexed" or not document_id:
            continue  # not a coverage gap the retrieval layer can fix — see compute_coverage_gaps()

        best_by_id: dict[str, dict[str, Any]] = {}
        for vector in vectors:
            hits = qdrant.search(
                workspace_id=workspace_id,
                query_vector=vector,
                limit=MAX_CHUNKS_PER_DOCUMENT,
                document_id=document_id,
            )
            for hit in hits:
                existing = best_by_id.get(hit["id"])
                if existing is None or hit["score"] > existing["score"]:
                    best_by_id[hit["id"]] = hit

        if not best_by_id:
            continue  # genuinely no chunks for this document — surfaced by compute_coverage_gaps()

        excerpt = _assemble_excerpt(list(best_by_id.values()), budget=remaining_budget)
        if not excerpt:
            continue

        supplemented.append({"filename": filename, "excerpt": excerpt})
        covered.add(filename)
        remaining_budget -= len(excerpt)

    return supplemented


def compute_coverage_gaps(
    sources: list[dict[str, str]], documents: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Pure diff between the final sources list and the workspace's known
    documents — used after retrieve_grouped_sources() (with document
    coverage enabled) to report, transparently, any document that still
    isn't represented rather than letting it silently vanish. Never
    touches Qdrant; safe to call unconditionally."""

    covered = {source["filename"] for source in sources}
    gaps: list[dict[str, str]] = []

    for document in documents:
        filename = str(document.get("filename") or "")
        if not filename or filename in covered:
            continue

        status = document.get("status")
        if status == "failed":
            reason = "processing_failed"
        elif status == "indexed":
            reason = "no_matching_evidence"
        else:
            reason = "not_yet_indexed"

        gaps.append({"filename": filename, "reason": reason})

    return gaps


def retrieve_grouped_sources(
    workspace_id: str,
    queries: list[str],
    *,
    embedder: EmbeddingService | None = None,
    qdrant: QdrantService | None = None,
    documents: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Embed each facet query, search Qdrant per facet (already scoped to
    `workspace_id` by QdrantService.search's own filter — see that method
    for the tenant-isolation guarantee this inherits), then merge, group by
    source document, and reassemble into one ranked excerpt per document.

    `documents`, when given (the workspace's full document list, each with
    id/filename/status — used only when the caller detected an explicit
    "use every document" instruction), guarantees every successfully-
    indexed document contributes at least some evidence even if the
    global relevance search above never surfaced it — see
    _ensure_document_coverage(). Omitted or empty, behavior is unchanged
    from before this existed: pure relevance-ranked retrieval.

    Returns [] whenever there's nothing useful to retrieve (nothing indexed
    for this workspace yet, no hits at all) — callers should treat an empty
    result as "fall back to a different source-gathering strategy", not as
    an error.
    """

    if not queries:
        return []

    embedder = embedder or EmbeddingService()
    qdrant = qdrant or QdrantService()

    vectors = embedder.embed_texts(queries)
    if not vectors:
        return []

    # Merge hits across every facet query, keyed by chunk id, keeping the
    # highest score seen — a chunk relevant to multiple facets is a
    # stronger signal, not a duplicate to discard.
    merged: dict[str, dict[str, Any]] = {}
    for vector in vectors:
        hits = qdrant.search(workspace_id=workspace_id, query_vector=vector, limit=FACET_TOP_K)
        for hit in hits:
            existing = merged.get(hit["id"])
            if existing is None or hit["score"] > existing["score"]:
                merged[hit["id"]] = hit

    if not merged and not documents:
        return []

    by_document: dict[str, list[dict[str, Any]]] = {}
    for hit in merged.values():
        key = hit["document_id"] or hit["filename"]
        if not key:
            continue
        by_document.setdefault(key, []).append(hit)

    # Rank documents by their single best-scoring chunk, drop anything
    # below the relevance floor (see MIN_DOCUMENT_RELEVANCE_SCORE), then
    # cap how many distinct documents make it into the report at all.
    # Both the floor and the cap bound the global-relevance stage only —
    # the coverage-guarantee stage below adds explicitly in-scope
    # documents regardless of either.
    ranked_documents = sorted(
        by_document.items(),
        key=lambda item: max(hit["score"] for hit in item[1]),
        reverse=True,
    )
    ranked_documents = [
        item for item in ranked_documents
        if max(hit["score"] for hit in item[1]) >= MIN_DOCUMENT_RELEVANCE_SCORE
    ][:MAX_DOCUMENTS]

    sources: list[dict[str, str]] = []
    seen_excerpts: set[str] = set()
    remaining_budget = TOTAL_BUDGET_CHARS

    for _document_key, hits in ranked_documents:
        if remaining_budget <= 0:
            break

        filename = hits[0]["filename"] or "document"
        excerpt = _assemble_excerpt(hits, budget=remaining_budget)
        if not excerpt:
            continue

        # Phase D: confirmed against real data — the same content indexed
        # twice under two filenames (e.g. an accidental re-upload) was
        # being presented as two independent corroborating sources,
        # inflating stated confidence ("supported by multiple documents")
        # and citation count for what is really one source counted
        # twice. An exact-text check is deliberately narrow — it only
        # catches a genuine duplicate, never a merely-similar document —
        # so it can't accidentally drop a real second source.
        if excerpt in seen_excerpts:
            continue
        seen_excerpts.add(excerpt)

        sources.append({"filename": filename, "excerpt": excerpt})
        remaining_budget -= len(excerpt)

    if documents:
        sources = _ensure_document_coverage(
            sources,
            documents=documents,
            vectors=vectors,
            workspace_id=workspace_id,
            qdrant=qdrant,
            remaining_budget=remaining_budget,
        )

    return sources
