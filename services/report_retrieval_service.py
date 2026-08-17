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


def _clip(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def retrieve_grouped_sources(
    workspace_id: str,
    queries: list[str],
    *,
    embedder: EmbeddingService | None = None,
    qdrant: QdrantService | None = None,
) -> list[dict[str, str]]:
    """Embed each facet query, search Qdrant per facet (already scoped to
    `workspace_id` by QdrantService.search's own filter — see that method
    for the tenant-isolation guarantee this inherits), then merge, group by
    source document, and reassemble into one ranked excerpt per document.

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

    if not merged:
        return []

    by_document: dict[str, list[dict[str, Any]]] = {}
    for hit in merged.values():
        key = hit["document_id"] or hit["filename"]
        if not key:
            continue
        by_document.setdefault(key, []).append(hit)

    # Rank documents by their single best-scoring chunk, cap how many
    # distinct documents make it into the report at all.
    ranked_documents = sorted(
        by_document.items(),
        key=lambda item: max(hit["score"] for hit in item[1]),
        reverse=True,
    )[:MAX_DOCUMENTS]

    sources: list[dict[str, str]] = []
    remaining_budget = TOTAL_BUDGET_CHARS

    for _document_key, hits in ranked_documents:
        if remaining_budget <= 0:
            break

        filename = hits[0]["filename"] or "document"

        # Selection is relevance-driven (a chunk from late in a long
        # document competes equally with one from the start), but the
        # chosen chunks are reassembled in original reading order so the
        # excerpt still reads coherently rather than as shuffled fragments.
        selected = sorted(hits, key=lambda hit: hit["score"], reverse=True)[:MAX_CHUNKS_PER_DOCUMENT]
        selected.sort(key=lambda hit: hit["chunk_index"])

        parts: list[str] = []
        previous_index: int | None = None
        for hit in selected:
            if previous_index is not None and hit["chunk_index"] > previous_index + 1:
                parts.append("[…]")
            parts.append(str(hit["text"]))
            previous_index = hit["chunk_index"]

        excerpt = _clip("\n\n".join(parts), min(PER_DOCUMENT_CHAR_CAP, remaining_budget))
        if not excerpt:
            continue

        sources.append({"filename": filename, "excerpt": excerpt})
        remaining_budget -= len(excerpt)

    return sources
